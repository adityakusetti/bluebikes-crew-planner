"""Bluebikes Crew Planner: Streamlit app.
Reads the tables exported by the notebook (app_data/*.csv) and adds a tool-calling assistant."""
import calendar
import json
import os

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Bluebikes Crew Planner", page_icon="🚲", layout="wide")

# Planning assumptions (same as the notebook)
SEASONAL_MONTH, SEASONAL_MIN_MONTHS, MAX_SEASONAL = 7_800, 3, 8
LOSS_PER_UNMET = 0.45 * 3.25 + 0.15 * (3.25 + 25)
CITIES = ["Boston", "Cambridge", "Somerville", "Brookline", "Other"]
MONTHS = {m: calendar.month_abbr[m] for m in range(1, 13)}


def capacity_per_crew(year, month):
    return 120 * 6 * calendar.monthrange(year, month)[1] / 7


@st.cache_data
def load(name):
    path = os.path.join("app_data", name)
    return pd.read_csv(path) if os.path.exists(path) else None


plan = load("plan.csv")
backtest = load("backtest.csv")
events = load("events.csv")
sens = load("sensitivity.csv")

st.title("🚲 Bluebikes Crew Planner")
st.caption("How many full-time and seasonal rebalancing crews each city needs in 2026, built from real Bluebikes trips.")

if plan is None:
    st.error("No data found. Run the notebook's export cell to create app_data/plan.csv, then reload.")
    st.stop()

# ---------- Headline numbers ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("2026 crew cost", f"${plan.crew_cost.sum():,.0f}")
c2.metric("Peak seasonal crews", f"{int(plan.groupby('month').seasonal.sum().max())} of {MAX_SEASONAL}")
if backtest is not None:
    short = backtest.shortfall_bikes.sum()
    c3.metric("Backtest shortfall (Jan–Sep)", f"{short:,.0f} bikes")
    c4.metric("Lost revenue in backtest", f"${short * LOSS_PER_UNMET:,.0f}")

tab_plan, tab_bt, tab_sens, tab_events, tab_chat = st.tabs(
    ["Crew plan", "Backtest", "Sensitivity", "Events", "Ask the assistant"])

# ---------- Crew plan ----------
with tab_plan:
    city = st.selectbox("City", [c for c in CITIES if c in set(plan.city)])
    p = plan[plan.city == city].sort_values("month")
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar(p.month, p.full_time, label="Full-time crews")
    ax.bar(p.month, p.seasonal, bottom=p.full_time, label="Seasonal crews")
    ax.plot(p.month, p.required, "k--o", label="Crews required")
    ax.set_xticks(list(MONTHS), list(MONTHS.values()))
    ax.set_ylabel("Crews"); ax.legend(loc="upper left"); ax.set_title(f"{city}: 2026 crew plan")
    st.pyplot(fig)
    cols = ["month", "need", "required", "full_time", "seasonal", "hires", "releases",
            "sign_seasonal_in", "unmet_bikes", "crew_cost", "lost_revenue"]
    show = p[[c for c in cols if c in p.columns]].copy()
    show["month"] = show["month"].map(MONTHS)
    st.dataframe(show.round(0), hide_index=True, use_container_width=True)
    st.caption("Full-time crews cover the year-round base; seasonal crews (signed a month ahead, 3-month minimum, "
               "at most 8 system-wide) cover the summer peak.")

# ---------- Backtest ----------
with tab_bt:
    if backtest is None:
        st.info("Export backtest.csv from the notebook to see this tab.")
    else:
        st.write("Planned crew capacity compared with the real rebalancing need in January–September 2026.")
        b = backtest[backtest.city == city].sort_values("month")
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.plot(b.month, b.actual_need, "o-", label="Actual need (real 2026 trips)")
        ax.plot(b.month, b.capacity, "s--", label="Planned crew capacity")
        ax.set_xticks(list(b.month), [MONTHS[m] for m in b.month])
        ax.set_ylabel("Bikes to move"); ax.legend(); ax.set_title(f"{city}: backtest")
        st.pyplot(fig)
        gaps = backtest[backtest.shortfall_bikes > 0][["city", "month", "actual_need", "capacity", "shortfall_bikes"]]
        gaps = gaps.assign(month=gaps.month.map(MONTHS))
        st.write("**Months where the plan would have fallen short**")
        st.dataframe(gaps.round(0), hide_index=True, use_container_width=True)

# ---------- Sensitivity ----------
with tab_sens:
    if sens is None:
        st.info("Export sensitivity.csv from the notebook to see this tab.")
    else:
        st.dataframe(sens.round(0), hide_index=True, use_container_width=True)
        st.caption("At +20% ridership the 8-crew seasonal cap binds and unmet need appears.")

# ---------- Events ----------
with tab_events:
    if events is None or events.empty:
        st.info("No events exported. Run the notebook's LLM event extractor first.")
    else:
        st.write("Events extracted by the LLM (structured output) from pasted event text.")
        st.dataframe(events, hide_index=True, use_container_width=True)


# ---------- Assistant (tool calling) ----------
def get_plan(city: str, month: int) -> dict:
    """Return the 2026 plan for one city and month (1-12)."""
    r = plan[(plan.city == city) & (plan.month == month)]
    if r.empty:
        return {"error": f"No plan for {city} in month {month}"}
    r = r.iloc[0]
    out = {"city": city, "month": calendar.month_name[month], "bikes_to_move": round(r.need),
           "full_time": int(r.full_time), "seasonal": int(r.seasonal), "unmet_bikes": round(r.unmet_bikes),
           "crew_cost": round(r.crew_cost)}
    if backtest is not None:
        bt = backtest[(backtest.city == city) & (backtest.month == month)]
        if not bt.empty:
            out["actual_2026_need"] = round(bt.iloc[0].actual_need)
            out["actual_shortfall_bikes"] = round(bt.iloc[0].shortfall_bikes)
    return out


def what_if(city: str, month: int, add_crews: int) -> dict:
    """Estimate the effect of adding (or removing, if negative) seasonal crews for one city and month."""
    r = plan[(plan.city == city) & (plan.month == month)]
    if r.empty:
        return {"error": f"No plan for {city} in month {month}"}
    r = r.iloc[0]
    need = r.need
    if backtest is not None:
        bt = backtest[(backtest.city == city) & (backtest.month == month)]
        if not bt.empty:
            need = max(need, bt.iloc[0].actual_need)
    new_capacity = r.capacity + add_crews * capacity_per_crew(2026, month)
    unmet_before, unmet_after = max(need - r.capacity, 0), max(need - new_capacity, 0)
    extra_cost = add_crews * SEASONAL_MONTH * (SEASONAL_MIN_MONTHS if add_crews > 0 else 1)
    return {"city": city, "month": calendar.month_name[month], "add_crews": add_crews,
            "unmet_bikes_before": round(unmet_before), "unmet_bikes_after": round(unmet_after),
            "extra_cost_incl_3_month_minimum": round(extra_cost),
            "revenue_saved": round((unmet_before - unmet_after) * LOSS_PER_UNMET),
            "seasonal_crews_system_wide": int(plan[plan.month == month].seasonal.sum() + max(add_crews, 0)),
            "seasonal_cap": MAX_SEASONAL}


def ask(question, history):
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import StructuredTool
    from langchain_openai import ChatOpenAI
    tools = {f.__name__: StructuredTool.from_function(f) for f in (get_plan, what_if)}
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(list(tools.values()))
    msgs = [SystemMessage("You help Bluebikes dispatchers with the 2026 crew plan. Always call a tool for numbers, "
                          "never guess. Cities: Boston, Cambridge, Somerville, Brookline, Other. Months are 1-12. "
                          "Mention the 8-crew seasonal cap and 3-month minimum when relevant. Keep answers short.")]
    for role, text in history[-6:]:
        msgs.append(HumanMessage(text) if role == "user" else AIMessage(text))
    msgs.append(HumanMessage(question))
    ai = llm.invoke(msgs)
    if not ai.tool_calls:
        return ai.content
    msgs.append(ai)
    for tc in ai.tool_calls:
        msgs.append(ToolMessage(content=json.dumps(tools[tc["name"]].invoke(tc["args"]), default=str),
                                tool_call_id=tc["id"]))
    return llm.invoke(msgs).content


with tab_chat:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        try:
            key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            key = None
    if key:
        os.environ["OPENAI_API_KEY"] = key
    st.write("Ask about the plan, for example *What happens if we add one crew to Cambridge in September?*")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for role, text in st.session_state.chat:
        st.chat_message(role).write(text)
    q = st.chat_input("Ask a question about the crew plan")
    if q:
        st.chat_message("user").write(q)
        if not key:
            answer = "Add OPENAI_API_KEY to Streamlit secrets (or your environment) to use the assistant."
        else:
            try:
                answer = ask(q, st.session_state.chat)
            except Exception as e:
                answer = f"Sorry, the assistant hit an error: {e}"
        st.chat_message("assistant").write(answer)
        st.session_state.chat += [("user", q), ("assistant", answer)]
