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
PATCHES: all of them, in order (what the test and the deploy step apply).
"""

COPIES = (
    ("front_camera_page.py", "app/pages/front_camera_page.py"),
    ("live_data_provider.py", "app/data/live_data_provider.py"),
    ("ride_quality_card.py", "app/widgets/ride_quality_card.py"),
    ("sw7_endpoints.py", "app/data/sw7_endpoints.py"),
    ("sw7_live_only.py", "app/data/sw7_live_only.py"),
    ("sw7_tile_map.py", "app/pages/sw7_tile_map.py"),
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
     "        if raw is not None and getattr(raw,'soc_pct',0) is None:\n"
     "            raise ValueError('Battery level unknown (no live BMS data), so no energy forecast can be made.')\n"
     "        soc=float(getattr(raw,'soc_pct',self.defaults.start_soc_pct)) if raw else self.defaults.start_soc_pct\n"),
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

PATCHES = WIRING_PATCHES + LIVE_ONLY_PATCHES + VEHICLE_PATCHES + TILE_MAP_PATCHES
