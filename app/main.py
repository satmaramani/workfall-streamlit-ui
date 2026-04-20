"""Streamlit UI for the multi-agent e-commerce demo."""

from __future__ import annotations

import streamlit as st

from config import (
    CONCIERGE_BASE_URL,
    INVENTORY_BASE_URL,
    INVOICE_BASE_URL,
    MARKET_INTELLIGENCE_BASE_URL,
    TRULENS_PORT,
)
from http_client import delete_json, get_json, post_json
from inventory_helpers import load_inventory_products, product_option_labels, product_option_map


def refresh_inventory_state() -> None:
    # Inventory is the source of truth for most dropdowns, so one refresh updates several tabs at once.
    products, error = load_inventory_products()
    st.session_state["inventory_products"] = products
    st.session_state["inventory_error"] = error


def sync_inventory_selection_keys() -> None:
    # When products change, this keeps stale widget selections from pointing at deleted product ids.
    products = st.session_state.get("inventory_products", [])
    product_ids = [item["product_id"] for item in products]
    if not product_ids:
        for key in ("inventory-delete-product", "invoice-product", "market-product"):
            st.session_state.pop(key, None)
        return

    for key in ("inventory-delete-product", "invoice-product", "market-product"):
        if st.session_state.get(key) not in product_ids:
            st.session_state[key] = product_ids[0]


def clear_market_result_if_matches(product_id: str) -> None:
    last_market_result = st.session_state.get("last_market_result")
    if isinstance(last_market_result, dict) and last_market_result.get("product_id") == product_id:
        st.session_state["last_market_result"] = None


def refresh_market_cache_snapshot(limit: int = 200) -> None:
    # The settings tab reads cache metadata from the backend so the UI never guesses cache state locally.
    result = get_json(f"{MARKET_INTELLIGENCE_BASE_URL}/api/v1/cache/market?limit={limit}", timeout=30.0)
    st.session_state["market_cache_snapshot"] = result["data"] if result["ok"] else None
    st.session_state["market_cache_error"] = None if result["ok"] else result["error"]


if "inventory_products" not in st.session_state or "inventory_error" not in st.session_state:
    refresh_inventory_state()
sync_inventory_selection_keys()
st.session_state.setdefault("last_invoice_result", None)
st.session_state.setdefault("last_concierge_result", None)
st.session_state.setdefault("last_market_result", None)
st.session_state.setdefault("market_cache_snapshot", None)
st.session_state.setdefault("market_cache_error", None)

pending_concierge_session = st.session_state.pop("pending_concierge_session_id", None)
if pending_concierge_session:
    st.session_state["last_session_id"] = pending_concierge_session
    st.session_state["concierge-session-id"] = pending_concierge_session
    st.session_state["trace-session-id"] = pending_concierge_session

inventory_products = st.session_state["inventory_products"]
inventory_error = st.session_state["inventory_error"]
inventory_options = product_option_labels(inventory_products)
inventory_option_map = product_option_map(inventory_products)


def render_key_value_table(data: dict, *, title: str | None = None) -> None:
    scalar_rows = []
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            continue
        scalar_rows.append({"Field": key.replace("_", " ").title(), "Value": value})
    if not scalar_rows:
        return
    if title:
        st.markdown(f"**{title}**")
    st.table(scalar_rows)


def render_inventory_table(products_payload: dict) -> None:
    products = products_payload.get("products", [])
    if not products:
        st.info("No inventory products found.")
        return

    st.markdown("**Inventory Catalog**")
    st.table(
        [
            {
                "Product ID": item.get("product_id"),
                "Product Name": item.get("product_name"),
                "Category": item.get("category"),
                "Available Quantity": item.get("quantity"),
                "Unit Price": item.get("unit_price"),
            }
            for item in products
        ]
    )

    with st.expander("Show raw inventory JSON"):
        st.json(products_payload)


def render_compact_invoice_result(result: dict) -> None:
    st.success(f"Invoice generated: {result.get('invoice_id', 'Unknown ID')}")
    top = st.columns(5)
    top[0].metric("Invoice ID", result.get("invoice_id", "-"))
    top[1].metric("Customer", result.get("customer_name", "-"))
    top[2].metric("Subtotal", result.get("subtotal", "-"))
    top[3].metric("Tax", result.get("tax_amount", "-"))
    top[4].metric("Total", result.get("total_amount", "-"))

    items = result.get("items", [])
    if items:
        st.markdown("**Items**")
        st.table(
            [
                {
                    "Product": item.get("product_name"),
                    "Quantity": item.get("quantity"),
                    "Unit Price": item.get("unit_price"),
                    "Line Total": item.get("line_total"),
                    "Pricing Source": item.get("pricing_source"),
                }
                for item in items
            ]
        )

    market_summaries = result.get("market_summaries", [])
    market_status = result.get("market_insight_status", "unknown")
    if market_status != "skipped":
        st.caption(
            f"Final invoice pricing may differ from the inventory base price because market pricing was "
            f"`{market_status}`."
        )
    if market_summaries:
        summary = market_summaries[0]
        st.markdown("**Market Pricing Summary**")
        st.write(summary.get("summary", ""))
        st.caption(
            f"Trend: {summary.get('trend', '-')}"
            f" | Recommended Price: {summary.get('recommended_price', '-')}"
            f" | Citations: {len(summary.get('citations', []))}"
        )

    workflow_steps = result.get("workflow_steps", [])
    if workflow_steps:
        st.markdown("**Downstream Workflow Steps**")
        st.table(workflow_steps)

    with st.expander("Show full invoice JSON"):
        st.json(result)


def render_compact_concierge_result(result: dict) -> None:
    st.success(result.get("message", "Workflow completed."))
    top = st.columns(4)
    top[0].metric("Status", result.get("status", "-"))
    top[1].metric("Intent", result.get("intent", "-"))
    top[2].metric("Session", result.get("session_id", "-"))
    top[3].metric("Backend", result.get("intent_resolution_backend", "-"))

    if result.get("agents_used"):
        st.markdown("**Agents Used**")
        st.write(", ".join(result["agents_used"]))

    workflow_steps = result.get("workflow_steps", [])
    if workflow_steps:
        st.markdown("**Workflow Steps**")
        st.table(workflow_steps)

    data = result.get("data")
    if isinstance(data, dict) and data.get("invoice_id"):
        render_compact_invoice_result(data)
    elif data:
        st.markdown("**Result Summary**")
        render_key_value_table(data)
        with st.expander("Show full result JSON"):
            st.json(data)

    with st.expander("Show full workflow JSON"):
        st.json(result)


def render_compact_market_result(result: dict) -> None:
    st.success(f"Market analysis ready for {result.get('product_name', 'product')}")
    cache = result.get("cache", {})
    # This top summary is meant to answer the first demo question immediately: live result or cache hit?
    top = st.columns(4)
    top[0].metric("Current Price", result.get("current_unit_price", "-"))
    top[1].metric("Recommended", result.get("recommended_price", "-"))
    top[2].metric("Cache Source", str(cache.get("source", "unknown")).replace("_", " ").title())
    cache_age = cache.get("cache_age_minutes")
    top[3].metric("Cache Age (min)", "-" if cache_age is None else cache_age)

    if cache:
        freshness_label = "stale" if cache.get("is_stale") else "fresh"
        st.caption(
            f"Cache enabled: `{cache.get('enabled')}`"
            f" | TTL: `{cache.get('ttl_minutes')}` minutes"
            f" | Freshness: `{freshness_label}`"
            f" | Cached at: `{cache.get('cached_at') or 'n/a'}`"
            f" | Expires at: `{cache.get('cache_expires_at') or 'n/a'}`"
            f" | Force refresh: `{cache.get('force_refresh')}`"
        )
        if cache.get("source") == "live_analysis":
            st.info("This result was generated live using current product context and then saved into cache.")
        elif cache.get("source") == "cache_hit":
            st.info("This result came from the saved market cache, so no fresh OpenAI call was needed.")
        elif cache.get("source") == "stale_cache_fallback":
            st.warning("Live market research failed, so the system served the most recent stale cached result.")

    st.markdown("**Trend**")
    st.write(result.get("trend", "-"))
    st.markdown("**Demand**")
    st.write(result.get("demand_signal", "-"))
    st.markdown("**Summary**")
    st.write(result.get("summary", ""))

    competitor_prices = result.get("competitor_prices", [])
    if competitor_prices:
        st.markdown("**Competitor Pricing**")
        st.table(
            [
                {
                    "Seller": item.get("seller"),
                    "Price": item.get("price"),
                    "Note": item.get("note"),
                }
                for item in competitor_prices
            ]
        )

    citations = result.get("citations", [])
    if citations:
        st.markdown("**Top Citations**")
        for citation in citations[:5]:
            st.markdown(f"- [{citation.get('title') or citation.get('url')}]({citation.get('url')})")

    history = result.get("internal_research_context", {}).get("recent_analyses", [])
    if history:
        st.markdown("**Recent Internal Research**")
        st.table(
            [
                {
                    "Created At": item.get("created_at"),
                    "Recommended Price": item.get("recommended_price"),
                    "Trend": item.get("trend"),
                }
                for item in history
            ]
        )

    with st.expander("Show full market JSON"):
        st.json(result)


def render_market_cache_snapshot(snapshot: dict) -> None:
    # The settings view is intentionally tabular so cache age and expiry are easy to compare in demos.
    st.markdown("**Market Cache Overview**")
    top = st.columns(4)
    top[0].metric("Cache Enabled", snapshot.get("cache_enabled", "-"))
    top[1].metric("TTL (min)", snapshot.get("cache_ttl_minutes", "-"))
    top[2].metric("Entries", snapshot.get("entry_count", 0))
    top[3].metric("Stale Fallback", snapshot.get("allow_stale_fallback", "-"))

    entries = snapshot.get("entries", [])
    if not entries:
        st.info("No market cache entries found yet.")
        return

    st.table(
        [
            {
                "Product ID": entry.get("product_id"),
                "Product Name": entry.get("product_name"),
                "Recommended Price": entry.get("recommended_price"),
                "Cached At": entry.get("created_at"),
                "Age (min)": entry.get("cache_age_minutes"),
                "Expires At": entry.get("cache_expires_at"),
                "Stale": entry.get("is_stale"),
            }
            for entry in entries
        ]
    )

    with st.expander("Show full cache JSON"):
        st.json(snapshot)


def render_trace_result(result: dict) -> None:
    events = result.get("events", [])
    st.markdown("**Trace Summary**")
    top = st.columns(2)
    top[0].metric("Session", result.get("session_id", "-"))
    top[1].metric("Events", len(events))

    if not events:
        st.info("No workflow trace events found for this session.")
    else:
        st.table(
            [
                {
                    "When": event.get("created_at"),
                    "Service": event.get("service_name"),
                    "Step": event.get("step_name"),
                    "Type": event.get("step_type"),
                    "Status": event.get("status"),
                    "Model": event.get("model_name"),
                }
                for event in events
            ]
        )

    with st.expander("Show full trace JSON"):
        st.json(result)


def render_health_report(health_report: dict) -> None:
    services = health_report.get("services", {})
    st.markdown("**Service Status**")
    if not services:
        st.info("No health data available.")
        return

    st.table(
        [
            {
                "Service": name,
                "Status": payload.get("status", "error"),
                "Port": payload.get("port", "-"),
                "DB Available": payload.get("db_available", "-"),
                "OpenAI": payload.get("openai_configured", "-"),
                "Details": payload.get("detail", ""),
            }
            for name, payload in services.items()
        ]
    )

    st.caption(f"TruLens dashboard URL: {health_report.get('trulens_dashboard_url', '-')}")
    with st.expander("Show full health JSON"):
        st.json(health_report)

st.set_page_config(page_title="Workfall Multi-Agent Commerce", layout="wide")
st.title("Workfall Multi-Agent E-Commerce")
st.caption("Concierge orchestration, inventory, invoice, market intelligence, and observability-ready UI.")

tab_concierge, tab_inventory, tab_invoice, tab_market, tab_settings, tab_trace, tab_health = st.tabs(
    ["Concierge", "Inventory", "Invoice", "Market", "Settings", "Trace", "Health"]
)

with tab_concierge:
    st.subheader("Concierge Request")
    user_input = st.text_area("Ask the system", value="Generate invoice for 2 laptop units", height=120)
    st.session_state.setdefault("concierge-session-id", st.session_state.get("last_session_id", ""))
    session_id = st.text_input("Session ID (optional)", key="concierge-session-id")
    include_market = st.toggle("Include market insights", value=True)
    if st.button("Send To Concierge", type="primary"):
        with st.spinner("Running concierge workflow across agents..."):
            result = post_json(
                f"{CONCIERGE_BASE_URL}/api/v1/workflows/request",
                {
                    "user_input": user_input,
                    "session_id": session_id or None,
                    "include_market_insights": include_market,
                },
                timeout=180.0,
            )
        if result["ok"]:
            st.session_state["last_concierge_result"] = result["data"]
            session = result["data"].get("session_id")
            if session:
                st.session_state["last_session_id"] = session
                st.session_state["pending_concierge_session_id"] = session
                st.rerun()
            else:
                render_compact_concierge_result(result["data"])
        else:
            st.session_state["last_concierge_result"] = None
            st.error(result["error"])

    if st.session_state.get("last_session_id") and not st.session_state.get("pending_concierge_session_id"):
        last_result = st.session_state.get("last_concierge_result")
        if last_result:
            render_compact_concierge_result(last_result)

with tab_inventory:
    st.subheader("Inventory Operations")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh Products"):
            with st.spinner("Refreshing inventory from Inventory Agent..."):
                refresh_inventory_state()
            st.rerun()
    with col2:
        if inventory_error:
            st.warning(f"Could not load live inventory: {inventory_error}")
        else:
            st.markdown(f"Loaded `{len(inventory_products)}` live products from Inventory Agent.")

    if not inventory_error and inventory_products:
        render_inventory_table({"products": inventory_products})

    with st.form("inventory-upsert-form"):
        product_id = st.text_input("Product ID", value="demo-product")
        product_name = st.text_input("Product Name", value="Demo Product")
        quantity = st.number_input("Quantity", min_value=0, value=10)
        unit_price = st.number_input("Unit Price", min_value=0.0, value=99.0)
        category = st.text_input("Category", value="general")
        merge_quantity = st.toggle(
            "If this product ID already exists, add this quantity to existing stock instead of replacing it",
            value=True,
            key="inventory-merge-quantity",
        )
        if st.form_submit_button("Save Product"):
            with st.spinner("Saving product in Inventory Agent..."):
                result = post_json(
                    f"{INVENTORY_BASE_URL}/api/v1/products",
                    {
                        "product_id": product_id,
                        "product_name": product_name,
                        "quantity": int(quantity),
                        "unit_price": float(unit_price),
                        "category": category,
                        "merge_quantity": merge_quantity,
                    },
                    timeout=30.0,
                )
            if result["ok"]:
                refresh_inventory_state()
                st.success(f"Saved product `{product_id}` successfully.")
                st.rerun()
            else:
                st.error(result["error"])

    st.markdown("**Delete Product**")
    if inventory_error:
        st.warning("Delete actions need live inventory data.")
    elif not inventory_products:
        st.info("No products available to delete.")
    else:
        delete_product_id = st.selectbox(
            "Product to Delete",
            [item["product_id"] for item in inventory_products],
            key="inventory-delete-product",
            format_func=lambda product_id: inventory_option_map.get(product_id, product_id),
        )
        delete_product = next(
            item for item in inventory_products if item["product_id"] == delete_product_id
        )
        if delete_product["quantity"] > 0:
            st.warning(
                f"This product still has {delete_product['quantity']} units in stock. "
                "Deleting it will permanently remove an in-stock product."
            )
        else:
            st.caption("This product has zero stock and is ready for deletion.")

        confirm_delete = st.checkbox(
            "I understand this deletion is permanent and may affect downstream workflows.",
            key="inventory-delete-confirm",
        )
        if st.button("Delete Product", type="secondary", key="inventory-delete-button"):
            if not confirm_delete:
                st.warning("Please confirm the deletion before continuing.")
            else:
                with st.spinner("Deleting product from Inventory Agent..."):
                    result = delete_json(
                        f"{INVENTORY_BASE_URL}/api/v1/products/{delete_product_id}",
                        timeout=30.0,
                    )
                if result["ok"]:
                    refresh_inventory_state()
                    if st.session_state.get("inventory-delete-product") == delete_product_id:
                        remaining_products = [item["product_id"] for item in st.session_state["inventory_products"]]
                        if remaining_products:
                            st.session_state["inventory-delete-product"] = remaining_products[0]
                    st.success(f"Deleted product `{delete_product_id}` successfully.")
                    st.rerun()
                else:
                    st.error(result["error"])

with tab_invoice:
    st.subheader("Invoice Preview")
    if inventory_error:
        st.error(f"Invoice form needs live inventory data: {inventory_error}")
    elif not inventory_products:
        st.warning("No products available in inventory. Add a product first from the Inventory tab.")
    else:
        with st.form("invoice-form"):
            product_ids = [item["product_id"] for item in inventory_products]
            selected_product_id = st.selectbox(
                "Product",
                product_ids,
                key="invoice-product",
                format_func=lambda product_id: inventory_option_map.get(product_id, product_id),
            )
            selected_product = next(
                item for item in inventory_products if item["product_id"] == selected_product_id
            )
            quantity = st.number_input("Quantity", min_value=1, value=1)
            customer_name = st.text_input("Customer Name", value="Internal Demo Customer")
            include_market = st.toggle("Use market insight for pricing", value=True, key="invoice-market")
            st.caption(
                f"Base inventory price for this product: {selected_product['unit_price']}. "
                "If market pricing is enabled, the final invoice unit price may increase or decrease."
            )
            if st.form_submit_button("Generate Invoice"):
                with st.spinner("Generating invoice and waiting for downstream agent responses..."):
                    result = post_json(
                        f"{INVOICE_BASE_URL}/api/v1/invoices",
                        {
                            "customer_name": customer_name,
                            "include_market_insights": include_market,
                            "session_id": st.session_state.get("last_session_id"),
                            "items": [{"product_id": selected_product["product_id"], "quantity": int(quantity)}],
                        },
                        timeout=180.0,
                    )
                if result["ok"]:
                    st.session_state["last_invoice_result"] = result["data"]
                    refresh_inventory_state()
                    sync_inventory_selection_keys()
                    st.rerun()
                else:
                    st.session_state["last_invoice_result"] = None
                    st.error(result["error"])

        if st.session_state.get("last_invoice_result"):
            render_compact_invoice_result(st.session_state["last_invoice_result"])

with tab_market:
    st.subheader("Market Intelligence")
    if inventory_error:
        st.error(f"Market form needs live inventory data: {inventory_error}")
    elif not inventory_products:
        st.warning("No products available in inventory. Add a product first from the Inventory tab.")
    else:
        product_ids = [item["product_id"] for item in inventory_products]
        selected_product_id = st.selectbox(
            "Market Product",
            product_ids,
            key="market-product",
            format_func=lambda product_id: inventory_option_map.get(product_id, product_id),
        )
        selected_product = next(
            item for item in inventory_products if item["product_id"] == selected_product_id
        )
        force_refresh_market = st.toggle(
            "Force fresh market research (bypass cache for this request)",
            value=False,
            key="market-force-refresh",
        )
        st.caption(
            "New products go live on the first request because no cache exists yet. "
            "Later requests can reuse the saved cache until the TTL expires."
        )
        if st.button("Fetch Market Insight"):
            with st.spinner("Researching market signals and competitor pricing..."):
                result = get_json(
                    f"{MARKET_INTELLIGENCE_BASE_URL}/api/v1/insights/{selected_product['product_id']}"
                    f"?force_refresh={'true' if force_refresh_market else 'false'}",
                    timeout=180.0,
                )
            if result["ok"]:
                st.session_state["last_market_result"] = result["data"]
                refresh_market_cache_snapshot()
            else:
                st.session_state["last_market_result"] = None
                st.error(result["error"])

        if st.session_state.get("last_market_result"):
            render_compact_market_result(st.session_state["last_market_result"])

with tab_settings:
    st.subheader("Settings & Cache Admin")
    st.markdown("**Market Cache Controls**")
    st.caption(
        "Use this tab to inspect cache freshness, clear one product cache for live demoing, "
        "or reset the full saved market cache."
    )
    control_col1, control_col2 = st.columns(2)
    with control_col1:
        if st.button("Load Market Cache Snapshot"):
            with st.spinner("Loading market cache metadata..."):
                refresh_market_cache_snapshot()
    with control_col2:
        if st.button("Refresh Inventory Context for Admin"):
            with st.spinner("Refreshing live inventory data..."):
                refresh_inventory_state()
            sync_inventory_selection_keys()
            st.rerun()

    if st.session_state.get("market_cache_error"):
        st.error(st.session_state["market_cache_error"])
    elif st.session_state.get("market_cache_snapshot"):
        render_market_cache_snapshot(st.session_state["market_cache_snapshot"])

    st.markdown("**Flush Market Cache**")
    if inventory_products:
        admin_product_id = st.selectbox(
            "Product Cache to Clear",
            [item["product_id"] for item in inventory_products],
            key="settings-market-cache-product",
            format_func=lambda product_id: inventory_option_map.get(product_id, product_id),
        )
        if st.button("Clear Selected Product Cache", type="secondary"):
            with st.spinner("Clearing selected product cache..."):
                result = delete_json(
                    f"{MARKET_INTELLIGENCE_BASE_URL}/api/v1/cache/market/{admin_product_id}",
                    timeout=30.0,
                )
            if result["ok"]:
                clear_market_result_if_matches(admin_product_id)
                refresh_market_cache_snapshot()
                st.success(
                    f"Cleared market cache for `{admin_product_id}`. "
                    "The next market lookup for this product will go live first."
                )
            else:
                st.error(result["error"])
    else:
        st.info("Load inventory products first to enable per-product cache clearing.")

    if st.button("Clear All Market Cache"):
        with st.spinner("Clearing all saved market cache entries..."):
            result = delete_json(f"{MARKET_INTELLIGENCE_BASE_URL}/api/v1/cache/market", timeout=30.0)
        if result["ok"]:
            st.session_state["last_market_result"] = None
            refresh_market_cache_snapshot()
            st.success("Cleared the full market cache. All next market lookups will go live first.")
        else:
            st.error(result["error"])

with tab_trace:
    st.subheader("Workflow Trace")
    st.session_state.setdefault("trace-session-id", st.session_state.get("last_session_id", ""))
    trace_session_id = st.text_input("Session ID for trace lookup", key="trace-session-id")
    if st.button("Load Trace"):
        if not trace_session_id:
            st.warning("Run a Concierge request first or enter a session ID.")
        else:
            with st.spinner("Loading workflow trace..."):
                result = get_json(f"{CONCIERGE_BASE_URL}/api/v1/traces/{trace_session_id}", timeout=20.0)
            if result["ok"]:
                render_trace_result(result["data"])
            else:
                st.error(result["error"])

with tab_health:
    st.subheader("Service Health")
    services = {
        "concierge": f"{CONCIERGE_BASE_URL}/api/v1/health",
        "inventory": f"{INVENTORY_BASE_URL}/api/v1/health",
        "invoice": f"{INVOICE_BASE_URL}/api/v1/health",
        "market": f"{MARKET_INTELLIGENCE_BASE_URL}/api/v1/health",
    }
    if st.button("Check All Services"):
        health_report = {}
        with st.spinner("Checking service health..."):
            for name, url in services.items():
                result = get_json(url, timeout=10.0)
                health_report[name] = result["data"] if result["ok"] else {"status": "error", "detail": result["error"]}
        render_health_report({"services": health_report, "trulens_dashboard_url": f"http://localhost:{TRULENS_PORT}"})
