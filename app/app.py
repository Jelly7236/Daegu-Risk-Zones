from shiny import App, ui
from modules import tab_analysis, tab_proposal, tab_notes1, tab_notes2

app_ui = ui.page_navbar(
    tab_analysis.panel(),
    tab_proposal.panel(),
    tab_notes1.panel(),
    tab_notes2.panel(),

    title="대구 화재 취약 지역 분석"
)

def server(input, output, session):
    tab_analysis.server(input, output, session)
    tab_proposal.server(input, output, session)
    tab_notes1.server(input, output, session)
    tab_notes2.server(input, output, session)

app = App(app_ui, server)