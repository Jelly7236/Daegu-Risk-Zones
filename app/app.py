from shiny import App, ui
from modules import overview

app_ui = ui.page_navbar(
    overview.panel(),  # 대구광역시 화재 현황
    
    ui.nav_panel("대구광역시 소방서, 소방용수시설, 건물 현황",
        ui.card(ui.h4("지리 레이어(예시)"), ui.p("소방서/소화전/건물 레이어 지도 추가 예정"))
    ),
    ui.nav_panel("대구광역시 화재취약지역 (분석된)",
        ui.card(ui.h4("취약도 지도/테이블(예시)"), ui.p("위험도 산식 및 결과 연결 예정"))
    ),
    ui.nav_panel("대구광역시에 제안 (달성군)",
        ui.card(ui.h4("달성군 제안서 초안"), ui.p("핵심 근거 지표/핫스팟/우선순위"))
    ),
    ui.nav_panel("대구광역시에 제안 (군위군)",
        ui.card(ui.h4("군위군 제안서 초안"), ui.p("핵심 근거 지표/핫스팟/우선순위"))
    ),
    title="대구 화재 대응취약지역 대시보드"
)

def server(input, output, session):
    overview.server(input, output, session)

app = App(app_ui, server)
