"""The edits README.md asks the dashboard team to make in v1.0-validated, as data.

test_live_data_provider.py applies them to a scratch copy of the dashboard and
starts the patched DashboardMain, so the README steps are checked, not only
described. Each entry: (file under the dashboard root, exact existing text,
replacement text). Every anchor must occur exactly once.
"""

COPIES = (
    ("front_camera_page.py", "app/pages/front_camera_page.py"),
    ("live_data_provider.py", "app/data/live_data_provider.py"),
    ("ride_quality_card.py", "app/widgets/ride_quality_card.py"),
)

CAMERA_DRAWER = '''def camera(p,r,c):
    _setup(p,c,max(1.6,r.width()*.065))
    body=QRectF(r.left()+r.width()*.14,r.top()+r.height()*.30,r.width()*.72,r.height()*.48)
    p.drawRoundedRect(body,r.width()*.08,r.width()*.08)
    p.drawRect(QRectF(r.left()+r.width()*.36,r.top()+r.height()*.20,r.width()*.22,r.height()*.10))
    p.drawEllipse(body.center(),r.width()*.14,r.width()*.14)


'''

PATCHES = (
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
    # dashboard_main.py: start the live provider and feed the ride card
    ("app/pages/dashboard_main.py",
     '        self._apply_theme(); self.switch_page_id("driving"); self.vehicle_data.start()\n',
     '        self._apply_theme(); self.switch_page_id("driving"); self.vehicle_data.start()\n'
     '        self.telemetry = LiveDataProvider(self.vehicle_data, parent=self)\n'
     '        self.telemetry.telemetry_updated.connect(self.diagnostics.ride_card.set_telemetry)\n'
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
