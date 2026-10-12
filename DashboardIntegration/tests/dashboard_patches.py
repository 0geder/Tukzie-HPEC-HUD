"""The edits README.md asks the dashboard team to make in v1.0-validated, as data.

test_live_data_provider.py applies them to a scratch copy of the dashboard and
starts the patched DashboardMain, so the README steps are checked, not only
described. Each entry: (file under the dashboard root, exact existing text,
replacement text). Every anchor must occur exactly once.

WIRING_PATCHES: the camera page, live-data provider and ride card wiring
(14 entries; their anchors were also checked on the Pi's v1.1).
LIVE_ONLY_PATCHES: live-only mode (TUKZIE_LIVE_ONLY=1, sw7_live_only.py) and
the None guards it needs in the pages. Without TUKZIE_LIVE_ONLY the manager
behaves as before; the page guards only act on values that are None. Their
anchors are checked against v1.0-validated only.
TILE_MAP_PATCHES: the street-tile map (sw7_tile_map.py) in place of the
team's NativeRouteMap, unless TUKZIE_TILE_MAP=0. Anchor checked in both
v1.0-validated and v1.1.
SETTINGS_PATCHES: finger-drag scrolling and a simpler Settings page (technical
options behind "Show advanced settings"). Anchors checked in v1.1.
LOGIN_PATCHES: skip the driver/PIN page when TUKZIE_SKIP_LOGIN=1.
SENSORS_PATCHES: the Sensors page on the nav bar and the hazard banner over every page.
ANALYTICS_CAROUSEL_PATCHES: the Analytics page as an infinite vertical carousel with a Graphs card.
DRIVING_PATCHES: large speed, battery and range in place of the dial and pedal bars.
SEARCH_PATCHES: destination search with Photon type-ahead, recents and a start-position header (sw7_search.py).
THEME_PATCHES: Night and Day themes, flat surfaces and the Atkinson Hyperlegible font (TUKZIE_SW7_THEME=0 restores the original).
LAYOUT_FRAME_PATCHES: the layout pass for the status bar, nav bar, side arrows, Settings and Charging
(sw7_layout_frame.py; TUKZIE_SW7_LAYOUT=0 restores the team's layout).
LAYOUT_DRIVE_PATCHES: the layout pass for Driving (TUKZIE_SW7_LAYOUT=0 restores the current look); Analytics' part is in sw7_analytics.py.
LAYOUT_PAGES_PATCHES: Diagnostics as four cards with the advice list folded away (sw7_layout_pages.py, added to
COPIES by LAYOUT_PAGES_COPIES); TUKZIE_SW7_LAYOUT=0 keeps the earlier layout.
LAYOUT_MAP_PATCHES: the Navigation page's overlays around the map's control column and turn banner (TUKZIE_SW7_LAYOUT=0 restores them).
STYLE_CORE_PATCHES: the paper and depth style, core (sw7_style.py and sw7_weather.py, added to COPIES by STYLE_CORE_COPIES):
palette, THEME in Paper or Ink, the frame (status bar, floating nav pill, arrows, chip, strip, obstacle pill) and the
Open-Meteo weather. TUKZIE_SW7_STYLE=team installs nothing (the layout-pass look).
STYLE_DRIVE_PATCHES: the paper style on Driving (the glance page: speed disc, Next turn, Around and Range tiles) and
Analytics (five cards, hero values, ink charts). No anchors: the code is in sw7_driving.py and sw7_analytics.py,
reached through the layout pass's own hooks; TUKZIE_SW7_STYLE=team leaves both pages as the layout pass drew them.
STYLE_PAGES_PATCHES: the paper and depth style, page agent P2 (sw7_style_pages.py, added to COPIES by
STYLE_PAGES_COPIES): Front camera and Sensors merged into Surroundings (7 nav items, page id "sensors", aliases
"camera" and "surroundings"), Diagnostics and Charging with one home per value. TUKZIE_SW7_STYLE=team: nothing.
STYLE_MAP_PATCHES: the paper style on the Map page's overlays and Settings (sw7_style_map.py, added to COPIES by
STYLE_MAP_COPIES); the map's own paper look is in sw7_tile_map.py. TUKZIE_SW7_STYLE=team installs nothing.
Tests: SETTINGS, LOGIN and SENSORS anchor on v1.1 only, so the tests run against a copy
of v1.1 (TUKZIE_DASHBOARD_DIR).
PATCHES: all of them, in order (what the test and the deploy step apply).
"""

COPIES = (
    ("front_camera_page.py", "app/pages/front_camera_page.py"),
    ("live_data_provider.py", "app/data/live_data_provider.py"),
    ("ride_quality_card.py", "app/widgets/ride_quality_card.py"),
    ("sw7_endpoints.py", "app/data/sw7_endpoints.py"),
    ("sw7_live_only.py", "app/data/sw7_live_only.py"),
    ("sw7_tile_map.py", "app/pages/sw7_tile_map.py"),
    ("sensors_page.py", "app/pages/sensors_page.py"),
    ("sw7_driving.py", "app/widgets/sw7_driving.py"),
    ("sw7_analytics.py", "app/pages/sw7_analytics.py"),
    ("sw7_sim_link.py", "app/pages/sw7_sim_link.py"),
    ("sw7_voice_guide.py", "app/pages/sw7_voice_guide.py"),
    ("sw7_touch.py", "app/pages/sw7_touch.py"),
    ("sw7_page_swipe.py", "app/pages/sw7_page_swipe.py"),
    ("sw7_search.py", "app/pages/sw7_search.py"),
    ("sw7_layout_frame.py", "app/widgets/sw7_layout_frame.py"),
    ("fonts/AtkinsonHyperlegible-Regular.ttf", "app/fonts/AtkinsonHyperlegible-Regular.ttf"),
    ("fonts/AtkinsonHyperlegible-Bold.ttf", "app/fonts/AtkinsonHyperlegible-Bold.ttf"),
    ("fonts/OFL.txt", "app/fonts/OFL.txt"),
)

CAMERA_DRAWER = '''def camera(p,r,c):
    _setup(p,c,max(1.6,r.width()*.065))
    body=QRectF(r.left()+r.width()*.14,r.top()+r.height()*.30,r.width()*.72,r.height()*.48)
    p.drawRoundedRect(body,r.width()*.08,r.width()*.08)
    p.drawRect(QRectF(r.left()+r.width()*.36,r.top()+r.height()*.20,r.width()*.22,r.height()*.10))
    p.drawEllipse(body.center(),r.width()*.14,r.width()*.14)


'''

WIRING_PATCHES = (
    # navigation_page.py: never create the web map when "Native fallback" is selected. On the Pi 5 the
    # Leaflet web map segfaults on the real display (PI5_MAP_CRASH.md), and it was created in the
    # background even when the native map was shown, so selecting Native fallback did not prevent the crash.
    ("app/pages/navigation_page.py",
     '        if QWebEngineView is None:\n'
     '            print("[WebEngine] QWebEngineView is None - falling back to offline map.")\n',
     '        if QWebEngineView is None or str(self.preferences.get("map_display_provider", "")) == "Native fallback":\n'
     '            print("[WebEngine] web map not created (unavailable or Native fallback selected) - using the native map.")\n'),
    # dashboard_main.py: imports
    ("app/pages/dashboard_main.py",
     "from ..data.data_provider import VehicleStateManager\n",
     "from ..data.data_provider import VehicleStateManager\n"
     "from ..data.live_data_provider import LiveDataProvider\n"),
    ("app/pages/dashboard_main.py",
     "from .driving_page import DrivingPage\n",
     "from .driving_page import DrivingPage\n"
     "from .front_camera_page import FrontCameraPage\n"),
    # dashboard_main.py: create the camera page and register it
    ("app/pages/dashboard_main.py",
     "        self.settings = SettingsPage(self.saved_settings)\n",
     "        self.settings = SettingsPage(self.saved_settings)\n"
     "        self.front_camera = FrontCameraPage()\n"),
    ("app/pages/dashboard_main.py",
     '            "settings": self.settings,\n',
     '            "settings": self.settings, "camera": self.front_camera,\n'),
    ("app/pages/dashboard_main.py",
     '        self.page_ids = ["driving", "analytics", "diagnostics", "navigation", "reverse", "charging", "settings"]\n',
     '        self.page_ids = ["driving", "analytics", "diagnostics", "navigation", "camera", "reverse", "charging", "settings"]\n'),
    ("app/pages/dashboard_main.py",
     '        self.normal_ids = ["driving", "analytics", "diagnostics", "navigation", "charging", "settings"]\n',
     '        self.normal_ids = ["driving", "analytics", "diagnostics", "navigation", "camera", "charging", "settings"]\n'),
    # dashboard_main.py: start the live provider, feed the ride card and show where the Pi 4 is
    ("app/pages/dashboard_main.py",
     '        self._apply_theme(); self.switch_page_id("driving"); self.vehicle_data.start()\n',
     '        self._apply_theme(); self.switch_page_id("driving"); self.vehicle_data.start()\n'
     '        self.telemetry = LiveDataProvider(self.vehicle_data, parent=self)\n'
     '        self.telemetry.telemetry_updated.connect(self.diagnostics.ride_card.set_telemetry)\n'
     '        self.telemetry.endpoint_changed.connect(self.diagnostics.ride_card.set_endpoint)\n'
     '        self.telemetry.start()\n'),
    ("app/pages/dashboard_main.py",
     '        for fn, name in ((self.vehicle_data.stop, "vehicle data"),',
     '        for fn, name in ((self.telemetry.stop, "telemetry"), (self.vehicle_data.stop, "vehicle data"),'),
    # diagnostics_page.py: the ride card under the diagnostics card
    ("app/pages/diagnostics_page.py",
     "from ..widgets.themed_surfaces import ThemedPageSurface, ThemedCard\n",
     "from ..widgets.themed_surfaces import ThemedPageSurface, ThemedCard\n"
     "from ..widgets.ride_quality_card import RideQualityCard\n"),
    ("app/pages/diagnostics_page.py",
     "        root.addWidget(card)\n",
     "        root.addWidget(card)\n"
     "        self.ride_card=RideQualityCard();root.addWidget(self.ride_card)\n"),
    # nav_bar.py: camera button
    ("app/widgets/nav_bar.py",
     "    ('navigation','navigation','Navigation'),\n",
     "    ('navigation','navigation','Navigation'),\n"
     "    ('camera','camera','Front camera'),\n"),
    # icon_registry.py: camera icon
    ("app/widgets/icon_registry.py",
     "DRAWERS: dict[str, DrawFn] = {\n",
     CAMERA_DRAWER + "DRAWERS: dict[str, DrawFn] = {\n"),
    ("app/widgets/icon_registry.py",
     "    'speaker': speaker,\n",
     "    'speaker': speaker, 'camera': camera,\n"),
)

ANALYTICS_OLD = (
    '        self.s_soc.set(f"{s.soc_pct:.0f} %")\n'
    '        self.s_btemp.set(f"{s.battery_temp_c:.0f} \\u00b0C")\n'
    '        self.s_atemp.set(f"{s.ambient_temp_c:.0f} \\u00b0C")\n'
    '        self.s_odo.set(f"{s.odometer_km:.1f} km")\n'
    '        self.s_power.set(f"{max(0.0, s.battery_power_kw):.1f} kW")\n'
    '        self.s_eff.set(f"{s.consumption_wh_km:.0f} Wh/km")\n'
    '\n'
    '        if self._tick % 15 == 0:\n'
    '            self.speed_chart.push(s.speed_kmh)\n'
    '            self.soc_chart.push(s.soc_pct)\n'
    '            self.dist_chart.push(s.odometer_km)\n'
    '            self.eff_chart.push(s.consumption_wh_km)\n'
)
ANALYTICS_NEW = (
    '        # SW-7: a value of None means no live data; show "--" and leave it out of the charts.\n'
    '        def _f(value, fmt):\n'
    '            return "--" if value is None else fmt.format(value)\n'
    '        self.s_soc.set(_f(s.soc_pct, "{:.0f} %"))\n'
    '        self.s_btemp.set(_f(s.battery_temp_c, "{:.0f} \\u00b0C"))\n'
    '        self.s_atemp.set(_f(s.ambient_temp_c, "{:.0f} \\u00b0C"))\n'
    '        self.s_odo.set(_f(s.odometer_km, "{:.1f} km"))\n'
    '        self.s_power.set(_f(None if s.battery_power_kw is None else max(0.0, s.battery_power_kw), "{:.1f} kW"))\n'
    '        self.s_eff.set(_f(s.consumption_wh_km, "{:.0f} Wh/km"))\n'
    '\n'
    '        if self._tick % 15 == 0:\n'
    '            for chart, value in ((self.speed_chart, s.speed_kmh), (self.soc_chart, s.soc_pct),\n'
    '                                 (self.dist_chart, s.odometer_km), (self.eff_chart, s.consumption_wh_km)):\n'
    '                if value is not None:\n'
    '                    chart.push(value)\n'
)

LIVE_ONLY_PATCHES = (
    # ---- data_provider.py: the manager in live-only mode --------------------------------------
    ("app/data/data_provider.py",
     "from ..asis.physics import estimate_remaining_range_km\n",
     "from ..asis.physics import estimate_remaining_range_km\n"
     "from .sw7_live_only import NO_DATA_MODE, live_only_enabled, no_data_state\n"),
    # __init__: in live-only mode start in the no-data state; the sim object only stores driver inputs
    ("app/data/data_provider.py",
     "        self._watchdog=QTimer(self); self._watchdog.setInterval(250); self._watchdog.timeout.connect(self._check_live_timeout)\n",
     "        self._watchdog=QTimer(self); self._watchdog.setInterval(250); self._watchdog.timeout.connect(self._check_live_timeout)\n"
     "        # SW-7 live-only mode (TUKZIE_LIVE_ONLY=1): the simulation never drives the display. Its state\n"
     "        # object only stores the driver inputs (gear, indicator, headlights, parking brake).\n"
     "        self.live_only=live_only_enabled()\n"
     "        if self.live_only:\n"
     "            self.sim.set_auto_drive(False); self.mode=NO_DATA_MODE; self.state=no_data_state(self.sim.state)\n"),
    # start(): never start the simulation timer in live-only mode
    ("app/data/data_provider.py",
     "    def start(self): self.sim.start(); self._watchdog.start()\n",
     "    def start(self):\n"
     "        if self.live_only:   # SW-7: no simulation; show the no-data state until live data arrives\n"
     "            self._watchdog.start(); self._publish_no_data(); return\n"
     "        self.sim.start(); self._watchdog.start()\n"),
    ("app/data/data_provider.py",
     "    def resume_auto_simulation(self): self.sim.set_auto_drive(True)\n",
     "    def resume_auto_simulation(self):\n"
     "        if not self.live_only: self.sim.set_auto_drive(True)\n"),
    ("app/data/data_provider.py",
     '        if self.mode=="live_controller": return\n',
     '        if self.mode=="live_controller" or self.live_only: return\n'),
    # watchdog: stale or missing live data goes to the no-data state, republished every 250 ms so the
    # driver inputs still update; never back to simulation
    ("app/data/data_provider.py",
     "    def _check_live_timeout(self):\n",
     "    def _publish_no_data(self):\n"
     "        state=no_data_state(self.sim.state); self.state=state; self.updated.emit(state)\n"
     "    def _check_live_timeout(self):\n"
     "        if self.live_only:   # SW-7: live data lost or not yet received -> explicit no-data state\n"
     "            if self.mode==\"live_controller\" and time.monotonic()<=self._live_deadline: return\n"
     "            if self.mode!=NO_DATA_MODE:\n"
     "                self.mode=NO_DATA_MODE; self._live_state=None; self.mode_changed.emit(self.mode)\n"
     "            self._publish_no_data(); return\n"),
    # _normalise_state: no state of charge means no range either (instead of float(None) failing)
    ("app/data/data_provider.py",
     "            state.soc_pct=max(0.0,min(100.0,float(state.soc_pct)))\n",
     "            if state.soc_pct is None:   # SW-7: no BMS data, so no state of charge and no range\n"
     "                state.range_km=None; return\n"
     "            state.soc_pct=max(0.0,min(100.0,float(state.soc_pct)))\n"),
    # ---- dashboard_main.py ---------------------------------------------------------------------
    ("app/pages/dashboard_main.py",
     '        if previous == "live_controller" and mode == "simulation":\n'
     '            self.toast.show_message("Controller disconnected · simulation resumed", 3500, "warning")\n',
     '        if previous == "live_controller" and mode == "simulation":\n'
     '            self.toast.show_message("Controller disconnected · simulation resumed", 3500, "warning")\n'
     '        elif previous == "live_controller" and mode == "no_data":\n'
     '            self.toast.show_message("Live data lost · showing no data", 3500, "warning")\n'),
    ("app/pages/dashboard_main.py",
     '            self.vehicle_data.resume_auto_simulation()\n'
     '            self.toast.show_message("Controller disconnected · simulation resumed", 3500, "warning")\n',
     '            self.vehicle_data.resume_auto_simulation()\n'
     '            self.toast.show_message("Controller disconnected" if getattr(self.vehicle_data, "live_only", False)\n'
     '                                    else "Controller disconnected · simulation resumed", 3500, "warning")\n'),
    # controller gear shift: with no brake sensor, use the controller's own brake input
    ("app/pages/dashboard_main.py",
     "            if self.current_state.brake_pct < 5:\n",
     "            if (self.current_state.brake_pct if self.current_state.brake_pct is not None\n"
     "                    else self.vehicle_data.sim._brake_intent) < 5:\n"),
    # ---- status_bar.py: "--%" and a grey battery when the state of charge is unknown -------------
    ("app/widgets/status_bar.py",
     "soc=float(getattr(s,'soc_pct',0.0) or 0.0); self.soc.setText(f'{soc:.0f}%'); ",
     "soc_known=getattr(s,'soc_pct',None) is not None; soc=float(getattr(s,'soc_pct',0.0) or 0.0); "
     "self.soc.setText(f'{soc:.0f}%' if soc_known else '--%'); self.battery._unknown=not soc_known; "),
    ("app/widgets/status_bar.py",
     "        return THEME.status('crit') if self._soc<=10 else",
     "        return THEME.color('text_faint') if getattr(self,'_unknown',False) else THEME.status('crit') if self._soc<=10 else"),
    # ---- driving_page.py: "--" for unknown speed, pedals and range ------------------------------
    ("app/pages/driving_page.py",
     "def set_values(self,speed,recommended=None): self.speed=",
     "def set_values(self,speed,recommended=None): self.speed_known=speed is not None; self.speed="),
    ("app/pages/driving_page.py",
     "Qt.AlignmentFlag.AlignCenter,f'{self.speed:.1f}')",
     "Qt.AlignmentFlag.AlignCenter,f'{self.speed:.1f}' if getattr(self,'speed_known',True) else '--')"),
    ("app/pages/driving_page.py",
     "self.speed.set_values(self.speed.speed,",
     "self.speed.set_values(self.speed.speed if getattr(self.speed,'speed_known',True) else None,"),
    ("app/pages/driving_page.py",
     "def set_value(self,value): self.value=",
     "def set_value(self,value): self.known=value is not None; self.value="),
    ("app/pages/driving_page.py",
     "f'{self.value*100:.0f}%')",
     "f'{self.value*100:.0f}%' if getattr(self,'known',True) else '--')"),
    ("app/pages/driving_page.py",
     "self.brake.set_value(getattr(s,'brake_pct',0)/100.0); self.accel.set_value(getattr(s,'throttle_pct',0)/100.0); "
     "self.range.setText(f'Range: {min(VEHICLE_SPEC.rated_max_range_km,float(getattr(s,\"range_km\",0) or 0)):.1f} km');",
     "self.brake.set_value(None if getattr(s,'brake_pct',0) is None else getattr(s,'brake_pct',0)/100.0); "
     "self.accel.set_value(None if getattr(s,'throttle_pct',0) is None else getattr(s,'throttle_pct',0)/100.0); "
     "self.range.setText('Range: -- km' if getattr(s,'range_km',0) is None else "
     "f'Range: {min(VEHICLE_SPEC.rated_max_range_km,float(getattr(s,\"range_km\",0) or 0)):.1f} km');"),
    # ---- diagnostics_page.py: unknown signed power is Unavailable, not +0.0 kW -------------------
    ("app/pages/diagnostics_page.py",
     "('Signed power',lambda s:f'{getattr(s,\"signed_battery_power_kw\",0) or 0:+.1f} kW')",
     "('Signed power',lambda s:f'{s.signed_battery_power_kw:+.1f} kW' if getattr(s,'signed_battery_power_kw',None) is not None else 'Unavailable')"),
    # ---- analytics_page.py ------------------------------------------------------------------------
    ("app/pages/analytics_page.py", ANALYTICS_OLD, ANALYTICS_NEW),
    # ---- charging_page.py: in live-only mode, no made-up voltage, current, power or temperature ---
    ("app/pages/charging_page.py",
     "import random\n",
     "import os\nimport random\n"),
    ("app/pages/charging_page.py",
     '        soc = max(0.0, min(100.0, float(getattr(s, "soc_pct", 0.0) or 0.0)))\n',
     '        soc = max(0.0, min(100.0, float(getattr(s, "soc_pct", 0.0) or 0.0)))\n'
     '        # SW-7: values with no live source are shown as "--" (live-only mode), and an unknown SOC always.\n'
     '        sw7_live_only = os.environ.get("TUKZIE_LIVE_ONLY", "").strip() == "1"\n'
     '        self.tuk.unknown = {"soc": getattr(s, "soc_pct", None) is None,\n'
     '                            "kw": sw7_live_only and source_kind == "unavailable",\n'
     '                            "v": sw7_live_only and getattr(s, "charging_voltage_v", None) is None,\n'
     '                            "a": sw7_live_only and getattr(s, "charging_current_a", None) is None,\n'
     '                            "temp": sw7_live_only and getattr(s, "battery_temp_c", None) is None}\n'),
    ("app/pages/charging_page.py",
     '        self.thermal_bar.set_temp(temp); self.thermal_value.setText(f"{temp:.1f} °C")\n',
     '        self.thermal_bar.set_temp(0.0 if self.tuk.unknown["temp"] else temp)\n'
     '        self.thermal_value.setText("--" if self.tuk.unknown["temp"] else f"{temp:.1f} °C")\n'),
    ("app/pages/charging_page.py",
     '            self.card_rate.value_label.setText("0.0 kW")\n',
     '            self.card_rate.value_label.setText("--" if self.tuk.unknown["kw"] else "0.0 kW")\n'),
    ("app/pages/charging_page.py",
     'Qt.AlignmentFlag.AlignCenter, f"{int(self.current_soc)}%")',
     'Qt.AlignmentFlag.AlignCenter, "--%" if getattr(self, "unknown", {}).get("soc") else f"{int(self.current_soc)}%")'),
    ("app/pages/charging_page.py",
     '        p.drawText(cx - 215, cy - 88,  f"{self.current_kw:.1f} kW")\n'
     '        p.drawText(cx - 215, cy + 2,   f"{self.current_v:.1f} V")\n'
     '        p.drawText(cx - 215, cy + 92,  f"{self.current_a:.1f} A")\n',
     '        unknown = getattr(self, "unknown", {})\n'
     '        p.drawText(cx - 215, cy - 88,  "-- kW" if unknown.get("kw") else f"{self.current_kw:.1f} kW")\n'
     '        p.drawText(cx - 215, cy + 2,   "-- V" if unknown.get("v") else f"{self.current_v:.1f} V")\n'
     '        p.drawText(cx - 215, cy + 92,  "-- A" if unknown.get("a") else f"{self.current_a:.1f} A")\n'),
    # ---- login_page.py ----------------------------------------------------------------------------
    ("app/pages/login_page.py",
     '        self.batt_lbl.setText(f"Battery {pct:.0f}%")',   # last line of the file, no newline
     '        self.batt_lbl.setText("Battery --%" if pct is None else f"Battery {pct:.0f}%")'),
    # ---- reverse_camera_page.py: no rear sensor, so no keyboard-simulated distance in live-only mode
    ("app/pages/reverse_camera_page.py",
     "        self.update_zone_indicators(self.distance)\n"
     "        self.update_ui(self.distance, self.angle)\n",
     "        self.update_zone_indicators(self.distance)\n"
     "        self.update_ui(self.distance, self.angle)\n"
     "        self._sw7_live_only = os.environ.get(\"TUKZIE_LIVE_ONLY\", \"\").strip() == \"1\"\n"
     "        if self._sw7_live_only:\n"
     "            self._sw7_no_rear_sensor()\n"),
    ("app/pages/reverse_camera_page.py",
     "    def keyPressEvent(self, event):\n",
     "    def _sw7_no_rear_sensor(self):\n"
     "        # SW-7 live-only mode: there is no rear distance sensor yet, so show none.\n"
     "        self.beep_timer.stop()\n"
     "        self.radar.hide()\n"
     "        self.distance_card.value_label.setText(\"--\")\n"
     "        self.debug_label.setText(\"Rear distance: no sensor\")\n"
     "        for label in self.legend_labels:\n"
     "            label.setStyleSheet(\"QFrame{background:transparent;border:none;border-radius:10px;}\")\n"
     "\n"
     "    def keyPressEvent(self, event):\n"
     "        if getattr(self, \"_sw7_live_only\", False):\n"
     "            return\n"),
    # ---- asis_advisory_panel.py: do not say "conditions normal" when ASIS has no telemetry ------------
    ("app/widgets/asis_advisory_panel.py",
     '        self.line1.setText("Route and vehicle conditions normal")\n',
     '        quality = getattr(getattr(self, "_support", None), "quality", None)\n'
     '        no_data = "telemetry" in (getattr(quality, "stale_flags", None) or [])   # SW-7\n'
     '        self.line1.setText("No live vehicle data" if no_data else "Route and vehicle conditions normal")\n'),
    # ---- ASIS ----------------------------------------------------------------------------------------
    # advice_engine.py: no battery advice from an unknown state of charge (it reads as 0 % in ASIS)
    ("app/asis/advice_engine.py",
     "        if s.soc_pct <= 8:\n",
     "        if (getattr(s, 'signal_validity', None) or {}).get('soc', True) is False:\n"
     "            return   # SW-7: state of charge unknown or stale; no battery advice from it\n"
     "        if s.soc_pct <= 8:\n"),
    # coordinator.py: no range from an unknown state of charge
    ("app/asis/coordinator.py",
     "        try: raw.range_km=estimate_remaining_range_km(self.spec,raw,self.defaults)\n",
     "        try: raw.range_km=estimate_remaining_range_km(self.spec,raw,self.defaults) if getattr(raw,'soc_pct',0) is not None else None\n"),
    ("app/asis/coordinator.py",
     "float(getattr(raw,'speed_kmh',0))<1.0",
     "float(getattr(raw,'speed_kmh',0) or 0)<1.0"),
    ("app/asis/coordinator.py",
     "        soc=float(getattr(raw,'soc_pct',self.defaults.start_soc_pct)) if raw else self.defaults.start_soc_pct\n",
     "        soc_unknown = raw is not None and getattr(raw,'soc_pct',0) is None   # SW-7 live-only: no BMS reading yet\n"
     "        soc=100.0 if soc_unknown else (float(getattr(raw,'soc_pct',self.defaults.start_soc_pct)) if raw else self.defaults.start_soc_pct)\n"),
    # coordinator.py: the route is planned without a battery reading; the energy forecast then assumes a
    # full battery and says so at the top of the warnings (a labelled assumption, not live data).
    ("app/asis/coordinator.py",
     "        warnings=[]\n        reserve=self.runtime.reserve_soc_pct\n",
     "        warnings=['Battery level unknown (no live BMS data): energy figures assume a full battery'] if soc_unknown else []\n        reserve=self.runtime.reserve_soc_pct\n"),
)

VEHICLE_PATCHES = (
    # dashboard_main.py: with TUKZIE_NO_CONTROLLER=1 the Xbox controller poller is not started.
    # The dashboard team measured it at about 53% of a CPU core (their README, known issue 6);
    # the vehicle is touch-only and the same Pi may also run the camera detector.
    ("app/pages/dashboard_main.py",
     "        if self.controller.backend_available:\n"
     "            self.controller.start()\n",
     "        if self.controller.backend_available and __import__(\"os\").environ.get(\"TUKZIE_NO_CONTROLLER\") != \"1\":\n"
     "            self.controller.start()\n"),
)

TILE_MAP_PATCHES = (
    # navigation_page.py: the native map becomes SW7TileMap (OpenStreetMap street tiles drawn with QPainter,
    # heading-up follow mode, disk cache; no QtWebEngine). Same API, so only the import changes.
    # TUKZIE_TILE_MAP=0 brings back the team's NativeRouteMap.
    ("app/pages/navigation_page.py",
     "from .navigation_page_fallback import NativeRouteMap\n",
     "from .navigation_page_fallback import NativeRouteMap\n"
     "if __import__(\"os\").environ.get(\"TUKZIE_TILE_MAP\", \"1\").strip() != \"0\":   # SW-7 street-tile map\n"
     "    from .sw7_tile_map import SW7TileMap as NativeRouteMap  # noqa: F811\n"),
)

SETTINGS_SIMPLIFY = '''    def _sw7_simplify(self):
        """SW-7: finger-drag scrolling, plain wording, technical options behind one switch."""
        from PySide6.QtWidgets import QScroller, QScrollerProperties
        QScroller.grabGesture(self.scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        sc = QScroller.scroller(self.scroll.viewport()); props = sc.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.ScrollMetric.MousePressEventDelay, 0.0)   # taps act at once
        sc.setScrollerProperties(props)
        nav = self.auto_follow.parentWidget().layout()
        nav.removeWidget(self.auto_follow); nav.addWidget(self.auto_follow, 5, 0, 1, 3)
        renames = {"ASIS voice": "Voice alerts", "Automatic vehicle following": "Map follows the tuk-tuk",
                   "Repeat last Critical advisory": "Repeat last warning", "SYSTEM COLOUR PALETTE": "COLOUR THEME",
                   "Speech speed": "Voice speed", "SYSTEM": "SAVE"}
        for kind in (QLabel, QCheckBox, QPushButton):
            for w in self.findChildren(kind):
                if w.text() in renames:
                    w.setText(renames[w.text()])
        self._sw7_advanced = []
        def rows(grid, wanted):
            for r in wanted:
                for c in range(grid.columnCount()):
                    item = grid.itemAtPosition(r, c)
                    if item and item.widget() and item.widget() not in self._sw7_advanced:
                        self._sw7_advanced.append(item.widget())
        rows(self.fullscreen.parentWidget().layout(), (1,))
        rows(self.map_provider.parentWidget().layout(), (1, 2, 3, 4, 6, 7, 8, 9))
        rows(self.voice_provider.parentWidget().layout(), (1,))
        self.sw7_show_advanced = QCheckBox("Show advanced settings")
        self.save_button.parentWidget().layout().insertWidget(1, self.sw7_show_advanced)
        self.sw7_show_advanced.toggled.connect(lambda on: [w.setVisible(on) for w in self._sw7_advanced])
        for w in self._sw7_advanced:
            w.setVisible(False)

'''

SETTINGS_PATCHES = (
    # settings_page.py: on the touchscreen the page could only be scrolled by its thin scroll bar, and it
    # showed developer options (route provider, ORS key, map engine, fallbacks, voice engine, kiosk mode)
    # next to the rider's. QScroller gives finger-drag scrolling; the technical rows are hidden behind
    # "Show advanced settings" (still created and saved as before, so preferences are unchanged).
    ("app/pages/settings_page.py",
     "        THEME.changed.connect(self._theme); self._theme()\n",
     "        THEME.changed.connect(self._theme); self._theme()\n"
     "        self._sw7_simplify()\n"),
    ("app/pages/settings_page.py",
     "    def _offline_toggled(self, enabled):\n",
     SETTINGS_SIMPLIFY + "    def _offline_toggled(self, enabled):\n"),
)

SENSORS_DRAWER = '''def sensors(p,r,c):
    _setup(p,c,max(1.6,r.width()*.065))
    cx,by=r.center().x(),r.top()+r.height()*.80
    p.drawEllipse(QPointF(cx,by),r.width()*.06,r.width()*.06)
    for k in (.22,.36):
        p.drawArc(QRectF(cx-r.width()*k,by-r.width()*k,2*r.width()*k,2*r.width()*k),45*16,90*16)


'''

SENSORS_PATCHES = (
    # A Sensors page (sensors_page.py) on the nav bar, so every reading can be opened at any time, and a
    # HazardBanner over every page: red for an "immediate" fusion hazard, amber when the bridge link is
    # lost; tapping it opens the Sensors page. Anchors include text added by WIRING_PATCHES.
    ("app/pages/dashboard_main.py",
     "from .front_camera_page import FrontCameraPage\n",
     "from .front_camera_page import FrontCameraPage\n"
     "from .sensors_page import HazardBanner, SensorsPage\n"),
    ("app/pages/dashboard_main.py",
     "        self.front_camera = FrontCameraPage()\n",
     "        self.front_camera = FrontCameraPage()\n"
     "        self.sensors = SensorsPage()\n"),
    ("app/pages/dashboard_main.py",
     '            "settings": self.settings, "camera": self.front_camera,\n',
     '            "settings": self.settings, "camera": self.front_camera, "sensors": self.sensors,\n'),
    ("app/pages/dashboard_main.py",
     '"navigation", "camera", "reverse", "charging", "settings"]\n',
     '"navigation", "camera", "sensors", "reverse", "charging", "settings"]\n'),
    ("app/pages/dashboard_main.py",
     '"navigation", "camera", "charging", "settings"]\n',
     '"navigation", "camera", "sensors", "charging", "settings"]\n'),
    ("app/pages/dashboard_main.py",
     '        self.telemetry.telemetry_updated.connect(self.diagnostics.ride_card.set_telemetry)\n',
     '        self.telemetry.telemetry_updated.connect(self.diagnostics.ride_card.set_telemetry)\n'
     '        self.telemetry.telemetry_updated.connect(self.sensors.set_telemetry)\n'
     '        self.hazard_banner = HazardBanner(self, lambda: self.stack.currentWidget() is self.sensors)\n'
     '        self.hazard_banner.open_sensors.connect(lambda: self.switch_page_id("sensors"))\n'
     '        self.telemetry.telemetry_updated.connect(self.hazard_banner.set_telemetry)\n'),
    ("app/widgets/nav_bar.py",
     "    ('camera','camera','Front camera'),\n",
     "    ('camera','camera','Front camera'),\n"
     "    ('sensors','sensors','Sensors'),\n"),
    ("app/widgets/icon_registry.py",
     "DRAWERS: dict[str, DrawFn] = {\n",
     SENSORS_DRAWER + "DRAWERS: dict[str, DrawFn] = {\n"),
    ("app/widgets/icon_registry.py",
     "    'speaker': speaker, 'camera': camera,\n",
     "    'speaker': speaker, 'camera': camera, 'sensors': sensors,\n"),
)

THEME_PATCHES = (
    # theme.py: two themes from Research/DashboardDesign (7 Oct 2026) replace the twelve palettes, unless
    # TUKZIE_SW7_THEME=0. Night is the default (dark, low glare); Day is for sunlight. Every text colour has a
    # contrast of at least 7:1 on its background. Status colours change with the theme so they keep that
    # contrast, and keep their meaning (green normal, amber warning, red critical).
    ("app/theme.py",
     '# The single light palette, used by the Dark/Light theme toggle.\n'
     'LIGHT_PALETTE_KEY = "arctic_white"\n',
     '# The single light palette, used by the Dark/Light theme toggle.\n'
     'LIGHT_PALETTE_KEY = "arctic_white"\n'
     '\n'
     '# SW-7 (Research/DashboardDesign): two themes, flat surfaces, a legible typeface. TUKZIE_SW7_THEME=0 restores the original.\n'
     'SW7_THEME = __import__("os").environ.get("TUKZIE_SW7_THEME", "1").strip() != "0"\n'
     'if SW7_THEME:\n'
     '    PALETTES = [\n'
     '        Palette("sw7_night", "Night", "Default \\u00b7 dark, low glare",\n'
     '                "#0E1116", "#171B22", "#80C0FF", "#3FD68A", "#F5F7FA"),\n'
     '        Palette("sw7_day", "Day", "Bright sunlight \\u00b7 dark text",\n'
     '                "#F7F8FA", "#FFFFFF", "#0947AA", "#0E5A2A", "#0B0D10"),\n'
     '    ]\n'
     '    LIGHT_PALETTE_KEY = "sw7_day"\n'
     '_SW7_STATUS = {False: {"normal": "#3FD68A", "warn": "#FFB224", "crit": "#FF857B", "inactive": "#7A8492"},\n'
     '               True: {"normal": "#0E5A2A", "warn": "#753F00", "crit": "#951B12", "inactive": "#8A94A0"}}\n'),
    ("app/theme.py",
     '        return QColor(_STATUS.get(key, _STATUS["inactive"]))\n',
     '        table = _SW7_STATUS[self.is_light] if SW7_THEME else _STATUS\n'
     '        return QColor(table.get(key, table["inactive"]))\n'),
    # theme.py: Atkinson Hyperlegible (Braille Institute, SIL OFL), shipped in app/fonts, first choice.
    ("app/theme.py",
     '        for candidate in ("Orbitron", "Rajdhani", "Inter", "Roboto",\n',
     '        if SW7_THEME:\n'
     '            import glob, os\n'
     '            for path in glob.glob(os.path.join(os.path.dirname(__file__), "fonts", "*.ttf")):\n'
     '                QFontDatabase.addApplicationFont(path)\n'
     '            families = set(QFontDatabase.families())\n'
     '            for candidate in ("Atkinson Hyperlegible", "B612", "Inter"):\n'
     '                if candidate in families:\n'
     '                    return candidate\n'
     '        for candidate in ("Orbitron", "Rajdhani", "Inter", "Roboto",\n'),
    # themed_surfaces.py: flat page and card surfaces (no gradient, no accent glow).
    ("app/widgets/themed_surfaces.py",
     'from ..theme import THEME\n',
     'from ..theme import SW7_THEME, THEME\n'),
    ("app/widgets/themed_surfaces.py",
     '        base = QLinearGradient(r.topLeft(), r.bottomRight())\n',
     '        if SW7_THEME:                      # flat background, no glow\n'
     '            p.fillRect(r, QColor(THEME.hex("bg")))\n'
     '            p.end()\n'
     '            super().paintEvent(event)\n'
     '            return\n'
     '        base = QLinearGradient(r.topLeft(), r.bottomRight())\n'),
    ("app/widgets/themed_surfaces.py",
     '        p.setBrush(grad)\n',
     '        p.setBrush(QColor(THEME.hex("card")) if SW7_THEME else grad)   # flat card in the SW-7 theme\n'),
)

DRIVING_PATCHES = (
    # driving_page.py: in the SW-7 theme the centre of the Driving page is SW7DrivePanel (sw7_driving.py):
    # a large speed number and battery and range tiles sized from Research/DashboardDesign, in place of the
    # 0 to 50 dial and the brake and accelerator bars (no pedal sensors on the vehicle). The route line is
    # larger. TUKZIE_SW7_THEME=0 keeps the team's layout.
    ("app/pages/driving_page.py",
     "from ..widgets.themed_surfaces import ThemedPageSurface\n",
     "from ..widgets.themed_surfaces import ThemedPageSurface\n"
     "from ..theme import SW7_THEME\n"
     "from ..widgets.sw7_driving import SW7DrivePanel\n"),
    ("app/pages/driving_page.py",
     "centre.addStretch(2); centre.addWidget(self.brake); centre.addWidget(self.speed,5); centre.addWidget(self.accel); centre.addStretch(2); root.addLayout(centre,2,0,1,3)",
     "self.sw7=None\n"
     "        if SW7_THEME:\n"
     "            self.sw7=SW7DrivePanel(); centre.addWidget(self.sw7,1)\n"
     "        else:\n"
     "            centre.addStretch(2); centre.addWidget(self.brake); centre.addWidget(self.speed,5); centre.addWidget(self.accel); centre.addStretch(2)\n"
     "        root.addLayout(centre,2,0,1,3)"),
    ("app/pages/driving_page.py",
     "        THEME.changed.connect(self._theme); self._theme()\n    def set_state(self,s):\n",
     "        if SW7_THEME:\n"
     "            self.range.hide(); self.route.setFont(THEME.font(22,QFont.Weight.DemiBold))\n"
     "        THEME.changed.connect(self._theme); self._theme()\n    def set_state(self,s):\n"
     "        if self.sw7 is not None: self.sw7.set_state(s)\n"),
)

ANALYTICS_CAROUSEL_PATCHES = (
    # analytics_page.py: the page's own value cards, chart cards and insights card are moved into an infinite
    # vertical carousel with a Graphs card that opens the four charts (sw7_analytics.py;
    # Planning/analytics-carousel-prompt.md). Only this page changes, and only its layout: update_state() and the
    # live-only handling are untouched. TUKZIE_ANALYTICS_CAROUSEL=0 keeps the original grid.
    ("app/pages/analytics_page.py",
     '        root.addWidget(self.insights)\n        self._latest_log = ""\n',
     '        root.addWidget(self.insights)\n        self._latest_log = ""\n'
     '        if __import__("os").environ.get("TUKZIE_ANALYTICS_CAROUSEL", "1").strip() != "0":   # SW-7 carousel\n'
     '            from .sw7_analytics import install_carousel\n'
     '            install_carousel(self, root, grid, chart_grid)\n'),
)

LOGIN_PATCHES = (
    # main_window.py: with TUKZIE_SKIP_LOGIN=1 the startup splash goes straight to the dashboard, without
    # the driver and PIN page (bench work). start_sw7_dashboard.sh sets it; set it to 0 for the demo.
    ("app/main_window.py",
     "    def _show_login(self):\n",
     "    def _show_login(self):\n"
     "        if __import__(\"os\").environ.get(\"TUKZIE_SKIP_LOGIN\") == \"1\":   # SW-7 bench: no PIN page\n"
     "            return self._enter_dashboard(\"\")\n"),
)

NAV_LAYOUT_PATCHES = (
    # navigation_page.py: the team's Route Guidance list is hidden. Our map's turn banner shows the next turn and
    # the one after (student, 11 Oct: "it seems its just taking space"), and the map then uses the full width
    # (sw7_tile_map._insets). TUKZIE_ROUTE_GUIDANCE=1 brings the panel back.
    ("app/pages/navigation_page.py",
     '        gt = QLabel("Route Guidance"); gt.setObjectName("guidanceTitle"); gt.setFont(THEME.font(15, QFont.Weight.Bold)); gl.addWidget(gt)\n',
     '        gt = QLabel("Route Guidance"); gt.setObjectName("guidanceTitle"); gt.setFont(THEME.font(15, QFont.Weight.Bold)); gl.addWidget(gt)\n'
     '        if __import__("os").environ.get("TUKZIE_ROUTE_GUIDANCE", "0").strip() != "1":   # SW-7: banner instead\n'
     '            self.guidance.hide()\n'),
)

SIM_LINK_PATCHES = (
    # dashboard_main.py: during the map's simulated drive every page gets one simulated vehicle state (speed,
    # battery, power, range, temperatures, trip from sw7_sim_link.SimDrive), with a SIMULATED DRIVE strip on every
    # page and a data-source chip (LIVE / REPLAY / NO DATA / SIMULATED) in the status bar. Obstacles, hazards and
    # the Sensors page stay live; the live state itself is kept in _sw7_live_state and never modified.
    # Planning/simulated-drive-sync-prompt.md.
    ("app/pages/dashboard_main.py",
     "    def _on_vehicle_state(self, state):\n        self.current_state = state\n",
     "    def _on_vehicle_state(self, state):\n"
     "        from .sw7_sim_link import sim_view   # SW-7: simulated drive in step on every page, labelled\n"
     "        self._sw7_live_state = state\n"
     "        state = sim_view(self, state)\n"
     "        self.current_state = state\n"),
    ("app/pages/dashboard_main.py",
     "        self.telemetry.start()\n",
     "        self.telemetry.start()\n"
     "        from .sw7_sim_link import connect as _sw7_sim_connect\n"
     "        _sw7_sim_connect(self)   # SW-7: each simulated-drive step refreshes the Driving page\n"
     "        from .sw7_voice_guide import install as _sw7_voice_guide\n"
     "        _sw7_voice_guide(self)   # SW-7: spoken turn-by-turn directions from the map's turn banner\n"
     "        from .sw7_touch import enable_all as _sw7_touch_scroll\n"
     "        _sw7_touch_scroll(self)   # SW-7: finger-drag scrolling on Diagnostics, Charging and every list\n"
     "        from .sw7_page_swipe import install as _sw7_page_swipe\n"
     "        _sw7_page_swipe(self)   # SW-7: two-finger swipe between pages (three on the map)\n"),
)

SEARCH_PATCHES = (
    # navigation_page.py: destination search like a ride-hailing app (sw7_search.py; Planning/destination-search-prompt.md).
    # Photon type-ahead biased to the current position, recents and offline matches shown at once, two-line rows with
    # distances, a "From:" header row, placeholder "Where to?". Only the destination field changes; the team's
    # request_suggestions stays the fallback and the path for any other field. TUKZIE_SW7_SEARCH=0 keeps the team's search.
    ("app/pages/navigation_page.py",
     "        timer.timeout.connect(lambda n=name, e=edit: self.coordinator.request_suggestions(n, e.text()))\n",
     "        from .sw7_search import enabled as _sw7_search_enabled\n"
     "        if name == \"destination\" and _sw7_search_enabled():   # SW-7: 120 ms debounce, Photon type-ahead\n"
     "            timer.setInterval(120)\n"
     "            timer.timeout.connect(lambda e=edit: self._sw7_search.request(e.text()) if getattr(self, \"_sw7_search\", None)\n"
     "                                  else self.coordinator.request_suggestions(\"destination\", e.text()))\n"
     "        else:\n"
     "            timer.timeout.connect(lambda n=name, e=edit: self.coordinator.request_suggestions(n, e.text()))\n"),
    ("app/pages/navigation_page.py",
     "            self.suggestions.setGeometry(p.x(), p.y() + 4, self.destination.width(), min(160, 32 * max(1, self.suggestions.count())))\n",
     "            if getattr(self, \"_sw7_search\", None) is not None:   # SW-7: two-line rows, up to five, above the keyboard\n"
     "                self.suggestions.setGeometry(self._sw7_search.list_geometry())\n"
     "            else:\n"
     "                self.suggestions.setGeometry(p.x(), p.y() + 4, self.destination.width(), min(160, 32 * max(1, self.suggestions.count())))\n"),
    ("app/pages/navigation_page.py",
     "        QTimer.singleShot(0, self._restore_latest_service_state)\n",
     "        QTimer.singleShot(0, self._restore_latest_service_state)\n"
     "        from .sw7_search import install as _sw7_search_install\n"
     "        _sw7_search_install(self)   # SW-7: destination search (sets self._sw7_search unless TUKZIE_SW7_SEARCH=0)\n"),
    # coordinator.py: with no GPS fix the route starts at the modem's network position, then the last known fix, and
    # only then at UCT; each start is labelled for what it is.
    ("app/asis/coordinator.py",
     "            return {'name':'Current location','label':'Current location','lat':float(lat),'lon':float(lon),'kind':'gps'}\n",
     "            return {'name':'Current location','label':'Current location','lat':float(lat),'lon':float(lon),'kind':'gps'}\n"
     "        if __import__('os').environ.get('TUKZIE_SW7_SEARCH','1').strip()!='0':   # SW-7: network position, then last fix\n"
     "            from ..pages.sw7_search import fallback_start\n"
     "            start=fallback_start(raw,self.last_asis_fix)\n"
     "            if start: return start\n"),
)

LAYOUT_FRAME_PATCHES = (
    # Layout pass, agent A (Planning/layout-improvements-prompt.md): status bar 48 px with 16 px text, nav bar 72 px
    # with labels and 64 px targets, side arrows in the nav bar's end margins, Settings in two columns with 64 px rows
    # and 64 x 36 toggles, Charging with one SOC figure (the status bar's rounding) and "5.8 of 7.2 kWh". The code is
    # in sw7_layout_frame.py, which wraps the team's classes once, before any page is built. TUKZIE_SW7_LAYOUT=0
    # installs nothing, so the team's layout is unchanged.
    ("app/pages/dashboard_main.py",
     "Dashboard = DashboardMain\n",
     "from ..widgets import sw7_layout_frame as _sw7_layout_frame   # SW-7 layout pass (TUKZIE_SW7_LAYOUT=0: off)\n"
     "_sw7_layout_frame.install_classes(DashboardMain)\n"
     "Dashboard = DashboardMain\n"),
    # charging_page.py: the ring's SOC rounded like the status bar (int() truncated: 79.6 % showed 79 % beside 80 %),
    # with the stored energy under it.
    ("app/pages/charging_page.py",
     "from ..widgets.nav_bar import Card\n",
     "from ..widgets.nav_bar import Card\n"
     "from ..widgets import sw7_layout_frame as _sw7_layout_frame\n"),
    ("app/pages/charging_page.py",
     "        p.drawText(QRectF(cx - 100, cy - 210, 200, 45),\n",
     "        if _sw7_layout_frame.enabled(): _sw7_layout_frame.paint_ring_soc(self, p, cx, cy)\n"
     "        else: p.drawText(QRectF(cx - 100, cy - 210, 200, 45),\n"),
)

LAYOUT_DRIVE_PATCHES = (
    # driving_page.py: the layout pass for the Driving page in the team look (sw7_driving.install_layout;
    # Planning/layout-improvements-prompt.md, agent B): 64 px advice strip across the page, whole-number speed at
    # 140 px in a larger dial, range and battery at 36 px under it, short pedal bars. TUKZIE_SW7_LAYOUT=0 (or the
    # SW-7 theme) leaves the page as it was. The Analytics part needs no patch: it is in sw7_analytics.py.
    ("app/pages/driving_page.py",
     "    def set_state(self,s):\n        if self.sw7 is not None: self.sw7.set_state(s)\n",
     "        from ..widgets.sw7_driving import install_layout as _sw7_layout\n"
     "        _sw7_layout(self)   # SW-7 layout pass (TUKZIE_SW7_LAYOUT, default on)\n"
     "    def set_state(self,s):\n        if self.sw7 is not None: self.sw7.set_state(s)\n"),
)

LAYOUT_PAGES_COPIES = (
    ("sw7_layout_pages.py", "app/pages/sw7_layout_pages.py"),
)
COPIES = COPIES + LAYOUT_PAGES_COPIES

LAYOUT_PAGES_PATCHES = (
    # diagnostics_page.py: four cards (Drive, Energy, Position, Link) in place of the one dense list, the ASIS,
    # route and voice list folded behind a 64 px "Show advice and details" row, the ride card hidden (ToF and
    # vibration are on Sensors; its link health is in the Link card). sw7_layout_pages.py; Planning/
    # layout-improvements-prompt.md (agent C). The Front camera and Sensors pages change in their own files.
    # TUKZIE_SW7_LAYOUT=0 keeps the earlier layout exactly.
    ("app/pages/diagnostics_page.py",
     "        root.addWidget(support);root.addStretch(1);THEME.changed.connect(self._theme);self._theme()\n",
     "        root.addWidget(support);root.addStretch(1);THEME.changed.connect(self._theme);self._theme()\n"
     "        from .sw7_layout_pages import enabled as _sw7_layout_on, install_diagnostics\n"
     "        if _sw7_layout_on(): install_diagnostics(self,root,card,separator,support_title,support)   # SW-7 layout\n"),
)

LAYOUT_MAP_PATCHES = (
    # navigation_page.py: layout pass on the map (Planning/layout-improvements-prompt.md, agent D). After the team's
    # overlays are placed, the map places them again around its own: the search field right of the turn banner,
    # Follow and Overview in the map's 64 x 64 control column (the team's small buttons hidden), the altitude card
    # replaced by the map's chip, the status line bottom left at 18 px (sw7_tile_map.SW7TileMap.layout_page).
    # TUKZIE_SW7_LAYOUT=0 (or TUKZIE_TILE_MAP=0, the team's map) leaves everything as it was.
    ("app/pages/navigation_page.py",
     "        for widget in (self.search, self.altitude, self.guidance, self.route_status, self.follow_btn, self.overview_btn, self.retry_btn, self.suggestions):\n"
     "            widget.raise_()\n",
     "        for widget in (self.search, self.altitude, self.guidance, self.route_status, self.follow_btn, self.overview_btn, self.retry_btn, self.suggestions):\n"
     "            widget.raise_()\n"
     "        if hasattr(self.map, \"layout_page\"):   # SW-7 layout pass: one control column, banner top left\n"
     "            self.map.layout_page(self)\n"),
    # a new route showed the team's Overview button again; with the layout pass Overview is in the map's column
    ("app/pages/navigation_page.py",
     "        self.overview_btn.show()\n",
     "        self.overview_btn.setVisible(not getattr(self.map, \"sw7_layout\", False))   # SW-7: Overview is in the map's column\n"),
)


STYLE_CORE_COPIES = (
    ("sw7_style.py", "app/widgets/sw7_style.py"),
    ("sw7_weather.py", "app/widgets/sw7_weather.py"),
)
COPIES = COPIES + STYLE_CORE_COPIES

STYLE_CORE_PATCHES = (
    # dashboard_main.py: the paper and depth style (Planning/paper-depth-theme-prompt.md, core). sw7_style.install wraps
    # the theme, the status bar, the nav bar and the shell after the layout pass has wrapped them; it does nothing with
    # TUKZIE_SW7_STYLE=team (or TUKZIE_SW7_LAYOUT=0).
    ("app/pages/dashboard_main.py",
     "_sw7_layout_frame.install_classes(DashboardMain)\n",
     "_sw7_layout_frame.install_classes(DashboardMain)\n"
     "from ..widgets import sw7_style as _sw7_style   # SW-7 paper and depth style (TUKZIE_SW7_STYLE=team: off)\n"
     "_sw7_style.install(DashboardMain)\n"),
)

STYLE_DRIVE_PATCHES = (
    # Paper and depth style, Driving and Analytics (Planning/paper-depth-theme-prompt.md section 10, agent P1). No
    # edits to the team's files are needed: sw7_driving.install_layout and sw7_analytics.install_carousel (already
    # called by LAYOUT_DRIVE_PATCHES and ANALYTICS_CAROUSEL_PATCHES) add the paper pages when sw7_style.enabled().
)

PATCHES = WIRING_PATCHES + LIVE_ONLY_PATCHES + VEHICLE_PATCHES + TILE_MAP_PATCHES + SETTINGS_PATCHES + LOGIN_PATCHES + SENSORS_PATCHES + THEME_PATCHES + DRIVING_PATCHES + ANALYTICS_CAROUSEL_PATCHES + NAV_LAYOUT_PATCHES + SIM_LINK_PATCHES + SEARCH_PATCHES + LAYOUT_FRAME_PATCHES + LAYOUT_DRIVE_PATCHES + LAYOUT_PAGES_PATCHES + LAYOUT_MAP_PATCHES + STYLE_CORE_PATCHES + STYLE_DRIVE_PATCHES


STYLE_PAGES_COPIES = (
    ("sw7_style_pages.py", "app/pages/sw7_style_pages.py"),
)
COPIES = COPIES + STYLE_PAGES_COPIES

STYLE_PAGES_PATCHES = (
    # dashboard_main.py: the paper and depth style for Surroundings (Front camera and Sensors as one page), Diagnostics
    # and Charging (Planning/paper-depth-theme-prompt.md section 10, page agent P2). sw7_style_pages.install wraps the
    # shell and the pages after sw7_style has; nothing with TUKZIE_SW7_STYLE=team, so the 8-page build is unchanged.
    # The anchor is the team's last line, so the group also applies (and does nothing) on a build without the core.
    ("app/pages/dashboard_main.py",
     "Dashboard = DashboardMain\n",
     "try:   # SW-7 paper style: Surroundings, Diagnostics, Charging (only on top of sw7_style)\n"
     "    from . import sw7_style_pages as _sw7_style_pages\n"
     "    _sw7_style_pages.install(DashboardMain)\n"
     "except ImportError:\n"
     "    pass\n"
     "Dashboard = DashboardMain\n"),
)
PATCHES = PATCHES + STYLE_PAGES_PATCHES
STYLE_MAP_COPIES = (
    ("sw7_style_map.py", "app/pages/sw7_style_map.py"),
)
COPIES = COPIES + STYLE_MAP_COPIES

STYLE_MAP_PATCHES = (
    # dashboard_main.py: the paper and depth style, page agent P3 (Planning/paper-depth-theme-prompt.md): the Map
    # page's search field, status line (one remaining-distance and ETA figure, in the map's arrival-time bar) and
    # touch keyboard, and Settings (paper cards, signal controls, the LOOK swatches in place of the colour theme
    # picker). The map's slab, tinted tiles, ink route and charcoal turn banner are in sw7_tile_map.py. Nothing with
    # TUKZIE_SW7_STYLE=team. Anchored on the file's last line (after sw7_style.install), so it also applies without
    # the core group (test_style_core's base build), where it installs nothing.
    ("app/pages/dashboard_main.py",
     "Dashboard = DashboardMain\n",
     "from .sw7_style_map import install as _sw7_style_map   # SW-7 paper style: Map and Settings\n"
     "_sw7_style_map(DashboardMain)\n"
     "Dashboard = DashboardMain\n"),
)
PATCHES = PATCHES + STYLE_MAP_PATCHES

STYLE_REFINE_COPIES = (
    # The UI theme refinement (Planning/ui-theme-refinement-prompt.md): IBM Plex Sans (Regular, Medium, SemiBold) for
    # the interface and IBM Plex Mono (Regular, Medium) for telemetry values, diagnostics, coordinates and timestamps,
    # from the official IBM/plex releases (@ibm/plex-sans@1.1.0, @ibm/plex-mono@1.1.0), SIL Open Font Licence 1.1
    # (OFL-IBMPlex.txt). sw7_style registers every TTF in app/fonts; Atkinson Hyperlegible stays as the fallback.
    ("fonts/IBMPlexSans-Regular.ttf", "app/fonts/IBMPlexSans-Regular.ttf"),
    ("fonts/IBMPlexSans-Medium.ttf", "app/fonts/IBMPlexSans-Medium.ttf"),
    ("fonts/IBMPlexSans-SemiBold.ttf", "app/fonts/IBMPlexSans-SemiBold.ttf"),
    ("fonts/IBMPlexMono-Regular.ttf", "app/fonts/IBMPlexMono-Regular.ttf"),
    ("fonts/IBMPlexMono-Medium.ttf", "app/fonts/IBMPlexMono-Medium.ttf"),
    ("fonts/OFL-IBMPlex.txt", "app/fonts/OFL-IBMPlex.txt"),
)
COPIES = COPIES + STYLE_REFINE_COPIES
# No STYLE_REFINE_PATCHES: the refinement changes our own modules only (sw7_style, sw7_weather, sw7_driving,
# sw7_analytics, sw7_style_pages, sw7_style_map, sw7_tile_map, sensors_page, front_camera_page), all behind
# TUKZIE_SW7_STYLE (team: nothing installed, as before).

STYLE_PLANES_COPIES = (
    # Three planes (Planning/three-planes-hero-prompt.md): the hero word face, Anton by Vernon Adams (google/fonts
    # ofl/anton, SIL Open Font Licence 1.1, OFL-Anton.txt), and the student's TUKZIE renders cut out of their white
    # backgrounds by tools/cut_tukzie_renders.py. sw7_style registers every TTF in app/fonts and loads the renders
    # from app/assets (cached, scaled once). No patches: our own modules only, all behind TUKZIE_SW7_STYLE.
    ("fonts/Anton-Regular.ttf", "app/fonts/Anton-Regular.ttf"),
    ("fonts/OFL-Anton.txt", "app/fonts/OFL-Anton.txt"),
    ("assets/tukzie_three_quarter.png", "app/assets/tukzie_three_quarter.png"),
    ("assets/tukzie_front.png", "app/assets/tukzie_front.png"),
    ("assets/tukzie_side.png", "app/assets/tukzie_side.png"),
)
COPIES = COPIES + STYLE_PLANES_COPIES
