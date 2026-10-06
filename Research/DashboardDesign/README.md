# Tukzie Driver Dashboard: Design Research

Compiled 6 October 2026 for SW-7 (Tukzie electric tuk-tuk, 1280x800 touchscreen, Raspberry Pi 5, PySide6).

## 1. Purpose

The current dashboard uses neon palettes, glows, gradients, small dim captions and many cards. This document collects credible evidence (standards, government reports, peer-reviewed studies, official platform guidelines and manufacturer statements) on what makes an in-vehicle display safe to read in a short glance, and turns it into concrete, numbered design rules and a recommended design direction for the redesign. Each rule cites a numbered source in Section 6; downloaded PDFs are in `papers/`.

How the sources were handled: ISO standards are paywalled, so their figures are quoted only through open secondary sources that state them, and this is flagged each time. Anything that could not be checked against a primary or credible secondary source is marked "not verified".

## 2. Key findings (design rules)

### 2.1 Glance time and distraction

1. Keep every glance under 2 s and the total eyes-off-road time for any task under 12 s. NHTSA's acceptance test requires that, for at least 21 of 24 drivers, the mean glance away from the road is 2.0 s or less, no more than 15 % of glances exceed 2.0 s, and the sum of glances for one task is 12.0 s or less (NHTSA 2013, [1], Section VI.E.14). NHTSA also states that glances longer than 2.0 s are associated with a statistically significant rise in crash and near-crash risk, and that the risk grows rapidly above 2.0 s [1].
2. Being stopped at a red light still counts as driving. NHTSA defines "driving" as any time the motor is active unless the vehicle is in Park (or, without a Park position, parking brake on, neutral and speed below 5 mph), and explicitly rejected a 5 mph threshold because drivers stopped in traffic may roll forward while distracted [1]. Analytics pages should therefore unlock only when the tuk-tuk is genuinely parked, not whenever speed reads zero.
3. Every task must be interruptible, and the system should not demand continuous attention. NHTSA lists "any task performed by a driver should be interruptible at any time" among its principles and recommends a response to input within 0.25 s, with a "busy" indication if the response takes longer than 2.0 s [1].
4. Do not show automatically scrolling text, video, or decorative or photographic images to the driver while moving. NHTSA lists these as per se lock-outs; maps are allowed, but photorealistic, satellite or 3D map detail is "not recommended" [1]. Android Automotive defines its no-video restriction as "no animated frames > 1fps" [11], which is a useful ceiling for decorative motion while moving.
5. Earlier industry criteria were looser and should not be the target. The Alliance of Automobile Manufacturers guideline (as described by NHTSA) allowed 20 s total glance time with a 2 s mean glance; NHTSA explained why it adopted 12 s instead, and also notes the JAMA (Japan) criterion of 8 s mean total eyes-off-road time [1]. The original Alliance document could not be downloaded (link dead), so these figures are taken from NHTSA's description.

### 2.2 Legibility

6. Character height (capital H) should subtend at least 20 arc minutes at the driver's eye; 16 arc minutes is "acceptable" and 12 arc minutes is a "minimum" only for reading with modest speed and accuracy needs. These are the ISO 15008 ratings as quoted by Reimer et al. (2014, [2]) and You et al. (2021, [3]); ISO 15008:2017 itself [4] is paywalled and was not read directly. ISO 15008 measures character height on the capital H, from baseline to cap line [2].
7. The US FHWA guideline gives the same scale and adds a tier for headline items: 30 arcmin minimum for titles and key elements, 20 arcmin for dynamic or critical elements, 16 arcmin for static or non-critical elements (Campbell, Carney and Kantowitz 1998, [5]).
8. Contrast: aim for 7:1. FHWA states 3:1 minimum and 7:1 preferred symbol contrast [5]. Google requires at least 4.5:1 for all text, icons and images in Android Auto and Android Automotive apps [8][10]. A figure circulating online attributes 5:1 (night), 3:1 (day and twilight) and 2:1 (direct sunlight) minimums to ISO 15008; this could not be traced to a citable source and is "not verified".
9. Use a typeface with open, clearly differentiated letterforms. In an MIT AgeLab and Monotype driving-simulator study, a humanist typeface (Frutiger) reduced total glance time by 10.6 % for male drivers compared with a square grotesque (Eurostile) at the same cap height, and error rates were 3.1 % lower for both sexes; the effect for women was smaller or absent [2]. Square, tightly spaced "techno" faces (Eurostile, Orbitron style) are the wrong choice for a driving screen.
10. Avoid thin weights and low-contrast "dim caption" styling. Apple's CarPlay guidance warns that "low-contrast colors can wash out in direct sunlight" and asks designers to test colour in an actual car across lighting conditions [12]. Google limits primary text to 32 dp and secondary text to 24 dp equivalents and caps any text item at 120 characters [8].
11. Night: use a dark (negative polarity) theme and keep total screen luminance low. Google requires night-time content to be negative polarity (light on dark) [8]. Mayr and Buchner (2010, [7], summarised in [6]) found that a bright positive-polarity car display impaired the later detection of low-contrast objects in a simulated night-driving task; the after-effect was strong for white and blue displays, reduced for amber and absent for red.
12. Day: a light (positive polarity) theme reads better, all else equal. Across many studies dark text on a light background gives better reading performance, attributed to smaller pupils under higher display luminance (Piepenbrock 2014, [6]). Google's platforms instead use a black background in both day and night for consistency [10]. For an open-sided tuk-tuk in Cape Town sun, the light day theme is the evidence-led default, but both themes must be tested on the real panel outdoors (Section 5.5).
13. Never rely on colour alone. Red-green colour vision deficiency affects up to 8 % of males and 0.5 % of females of Northern European descent (Almustanyir 2025, [32]). Pair every colour state with an icon, a word and a fixed position. Apple asks for colours that "communicate effectively with everyone" [12].
14. Use colour by convention and sparingly. FHWA: green for OK, yellow for caution, red for hazard, and avoid highly saturated blue (about 450 nm) [5]. UN Regulation 121 fixes tell-tale colours (for example red for brake failure and seat belt, yellow for ABS and engine malfunction, blue for main beam) and points to ISO 2575 colour coding for anything not listed [16]. (R121 legally covers M and N category vehicles, not L-category three-wheelers; it is used here as the established convention.) Apple: avoid using the same colour for interactive and non-interactive elements [12]. Google: grey scale on black, one accent colour used sparingly [10].

### 2.3 Information hierarchy, alerts and touch

15. Put the most important information highest and closest to the driver's line of sight. NHTSA: displays with frequently needed or important driving information should have downward viewing angles "as close as practicable to a driver's forward line of sight" [1]. Apple: place the most important content and controls in the upper half of the screen and do not clutter it with "nonessential details and unnecessary visual embellishments" [12]. Euro NCAP 2026 requires speed and assistance status to be in the driver's direct line of sight [13].
16. Safety-critical warnings must take priority over anything else in a shared display area. UN R121: when a common space shows several messages, the brake-failure, main-beam, turn-indicator and seat-belt tell-tales must displace any other symbol when their condition exists, and cannot be cancelled by the driver [16]. Apply the same rule to the Tukzie critical alerts.
17. Urgent warnings should be multimodal. FHWA: "a combination of alerting tones, speech messages, and icons would best present hazard warning information", and an auditory alerting cue combined with a visual display gives fast responses [5].
18. Touch targets for a moving vehicle must be much larger than phone targets. Euro NCAP 2026: digital touch controls need at least 10 x 10 mm with 4 mm separation [13]. Google: minimum 76 x 76 dp (about 12 mm) with at least 23 dp between targets, and targets must not overlap [8][9]. In a simulator study with keys from 7.5 to 27.5 mm, driving safety and usability improved up to 17.5 mm and then levelled off (Kim et al. 2014, [14]; earlier Korean report [15]).
19. Keep primary driving controls physical where possible. Euro NCAP 2026 requires indicators, hazard lights, horn, gear selection and eCall to be "direct physical input" for points; a direct physical input is defined as one the driver can find by touch with minimal gaze off-road and that gives haptic feedback [13]. For Tukzie: the touchscreen must never be the only way to operate indicators, hazards, horn or drive mode.
20. Restrict content while moving rather than only shrinking it. Android Automotive maps driving states as: parked, unrestricted; idling, no video and no configuration screens; moving, fully restricted (no keyboard, limited string length, limited list items and depth, no video) [11]. Apple lets the car limit list and keyboard display in CarPlay while driving [12]. Tesla locked its in-car games while moving after NHTSA opened an investigation covering about 580,000 vehicles in December 2021 [26].

### 2.4 Evidence that touch-heavy screens cost glance time

21. In a TRL simulator study for IAM RoadSmart, selecting music by touch in Android Auto or Apple CarPlay increased reaction time more than previously measured impairments including texting and hand-held calls; touch was more distracting than voice (Ramnath et al. 2020, [18]). Press coverage of the same study reports eyes-off-road of up to 16 s and reaction times slowed by 53 % (Android Auto) and 57 % (CarPlay) [18]; those two percentages come from the press release and were not checked against the full report.
22. In the AAA Foundation and University of Utah study of 30 model-year 2017 vehicles, 23 produced high or very high overall demand and none was low; texting averaged 30 s and navigation destination entry 40 s, far beyond NHTSA's 12 s (Strayer et al. 2017, [17]).
23. Vi Bilägare (Sweden, 2022) timed four simple tasks at 110 km/h in 12 cars: a 2005 Volvo V70 with physical buttons took 10 s (306 m); the best modern car 13.5 s; the worst, an MG Marvel R, 44.9 s (about 1,372 m) [19]. This is a magazine test, not peer-reviewed, but it is widely cited and its method is published.
24. Industry reaction: Euro NCAP's 2026 protocol now scores physical controls [13], and Volkswagen's design chief said "customers say a pure touchscreen is not enough and they expect physical switches" as VW reintroduced buttons (Carscoops 2023, [27]).

## 3. Production references

The question for each product was: palette, type, layout, what was left out, and any published rationale. Where no first-party rationale exists, that is stated.

### 3.1 Platform guidelines (the most directly usable references)

| Platform | Palette | Type and size | Layout and restrictions | Source |
|---|---|---|---|---|
| Android Auto / Android Automotive OS | True black background in day and night; grey steps for hierarchy; one saturated blue accent "used sparingly"; contrast at least 4.5:1 | Primary text 32 dp, secondary 24 dp; max 120 characters per text item; primary icons 44 dp | Touch targets at least 76 dp, 23 dp apart; night content must be negative polarity; driving-state restrictions (no video above 1 fps, no keyboard, limited list depth) | [8][9][10][11] |
| Apple CarPlay | Light and dark appearances, can switch automatically with lighting; "limited color palette"; never the same colour for interactive and non-interactive elements | System templates; avoid clutter and "unnecessary visual embellishments" | Most important content in the upper half; app must work without touching the phone; car can limit lists and keyboard while moving | [12] |

What they deliberately leave out: free-form custom layouts (third-party apps get templates only), video, decorative imagery, and text entry while driving.

### 3.2 Tesla Model 3 / Model Y

- Layout: no instrument cluster; the driver-side third of the centre screen shows speed (top left, closest to the driver), gear and driver-assistance visualisation; the rest is map. The speed readout turns red when speeding (Fortune / The Drive 2017, [25]).
- Left out: a conventional cluster behind the wheel. A Tesla engineer reported that not having the cluster's glare in front of him helped at night (reported in [25] and other press; first-party quote not verified).
- Lock-outs: in-car games were locked while moving after the 2021 NHTSA investigation [26].
- Rationale: Tesla has not published a design rationale document; statements are from interviews and press.

### 3.3 Polestar 2 (first Android Automotive car)

- Palette and style: Polestar describes a "minimalist" interface "designed for optimal performance" instead of "riotous colour schemes and frenetic font combinations" (Polestar Journal 12.2, 2019, [21]).
- Layout: replaced "unwieldy collapsible menus" with a four-tile grid [21].
- Rationale, first party: Aloka Muddukrishna (User Experience): "UIs tend not to be driver oriented. They also have comparatively small touch areas, taking more of your attention which should be on the road." Amil Gasanin (graphic designer): "A bigger touch area is always beneficial, and helps to minimise driver distraction." [21]
- Left out: dense menus and decorative colour.

### 3.4 Volkswagen ID. family

- Layout: a small driver display behind the wheel with core driving data, everything else on the centre touchscreen; capacitive steering-wheel pads and touch sliders.
- Outcome: heavy criticism; VW leadership said customers expect physical switches, and the ID. 2all concept brought back a row of physical buttons and a rotary controller [27]. This is the clearest production example of a touch-only approach being reversed.

### 3.5 BYD Atto 3 and Dolphin

- Layout: large rotating centre touchscreen (12.8 or 15.6 inch in the Atto 3) plus a small (about 5 inch) driver display on the steering column (Parkers review, [28]).
- Criticism: reviewers report small icons and several menu layers for common functions; portrait mode partly blocks the view, so drivers return to landscape [28].
- Rationale: BYD has not published a design rationale that could be found; BYD has since said it will phase out the rotating screen (press reports, not verified first party).

### 3.6 Rivian

- Style: Rivian rebuilt its UI in Unreal Engine with an illustrated, colourful "optimistic" look, according to Chief Design Officer Jeff Hammoud (InsideEVs interview and Epic Games case study, [29]). These pages could not be opened during this research (blocked), so the description relies on search-engine excerpts and is "partly verified".
- Relevance: Rivian is the counter-example. Its expressive style is mainly for parked or passenger moments; nothing published shows it reduces glance time. It should not be the model for a safety-focused driving page.

### 3.7 Uber Driver app

- Map first: the 2017 navigation redesign added lane guidance, compound manoeuvres and "Route Preview" showing the first turn after a pickup or drop-off (Uber Newsroom 2017, [22]).
- Night mode story: the 2017 release introduced "night-time themed maps to help give drivers' eyes a break from harsh light during the evenings" [22]. Uber's help centre states the app "switches to darker colors automatically" with Always off, Always on or Automatic settings [23]. Uber's design team wrote that the default day colours caused eye strain as drivers readjusted from the bright screen to dark streets, and that designers chose the subdued night palette by viewing candidate schemes in a windowless dark room and then on night drives ("Uber Navigation: Designing for drivers", Uber Design on Medium, [24]). That article was blocked to automated access; this summary comes from search-engine excerpts of it and is "partly verified".
- Speed: optional speed-limit alerts shown "right on the map", with thresholds of 1, 10 or 15 km/h over the limit (Uber Newsroom NZ 2018, [30]).
- Glanceable earnings at the top of the screen in the 2018 "Carbon" driver app [22a].
- Left out: Uber has not published restrictions on which driver-app screens are locked while moving; not verified either way.

### 3.8 Bolt Driver app

- No first-party design rationale, theme description or published design guideline for the Bolt Driver app could be found from Bolt or reputable press. Public Bolt material focuses on earnings and safety features (SOS button, trip sharing, rider scoring) rather than display design (Connecting Africa 2022, [31]). Treat any claim about Bolt's palette or night mode as "not verified".

### 3.9 Electric ride-hailing vehicles

- BYD D1 (DiDi, 2020), the first EV designed for ride-hailing: the platform runs on a 10.1 inch "pad" on the dashboard so the driver does not need a personal phone, with a small separate display behind the wheel for speed (KrASIA 2020, [33]; the separate speed display is from CleanTechnica and other press, not verified first party). The relevant lesson is the split: driving data in a small fixed display in the line of sight, platform workflow on a separate screen. Note that the D1 pad is the same diagonal and resolution class as the Tukzie panel.
- In most markets, ride-hailing EVs (Tesla, BYD, Kia, Hyundai) use the standard vehicle cluster plus a phone running the Uber or Bolt app, so the driver's two displays follow the platform and phone app conventions above.

### 3.10 Electric two- and three-wheelers

- Gogoro Pulse (2024): 10.25 inch touch display with turn-by-turn navigation and ride modes, ride-mode selection on a dedicated handlebar dial rather than the screen (Gogoro press release, [34]).
- Ather 450 series: 7 inch TFT touchscreen; Ather markets sunlight readability, but its blog was blocked to automated access and no independent measurement was found ("not verified").
- Bajaj, Piaggio and other electric autorickshaws: no published HMI design rationale was found. This gap is worth stating in the report: there is no public, evidence-based dashboard guideline for electric three-wheelers, which is part of what makes the Tukzie work original.

## 4. Recommended design direction for the Tukzie dashboard

### 4.1 Panel and viewing assumptions

- Assumed panel: 10.1 inch diagonal, 1280 x 800, square pixels. Pixel density = sqrt(1280^2 + 800^2) / 10.1 = 1509.4 / 10.1 = 149.4 ppi. Pixel pitch = 25.4 / 149.4 = 0.170 mm. Active area about 218 x 136 mm.
- Viewing distance: 70 cm nominal. Sizes are also checked at 80 cm (worst case) because the driver sits upright on a bench seat and leans back.
- Formula: cap height h = 2 d tan(theta / 2), with theta in arc minutes / 60 converted to degrees.
- Qt note: `QFont.setPixelSize()` sets the em size, not the cap height. Font px = cap px / (cap-height ratio). Measured cap-height ratios from the font files: Atkinson Hyperlegible 0.668, B612 0.75 (H glyph 0.76), Inter 0.728.

### 4.2 Minimum sizes

| Arc minutes | Cap height at 70 cm | Cap px at 70 cm | Cap px at 80 cm | Font px (Atkinson) at 70 / 80 cm |
|---|---|---|---|---|
| 12 (ISO "minimum") | 2.44 mm | 14 | 16 | 22 / 25 |
| 16 (ISO "acceptable", FHWA static) | 3.26 mm | 19 | 22 | 29 / 33 |
| 20 (ISO "recommended", FHWA critical) | 4.07 mm | 24 | 27 | 36 / 41 |
| 30 (FHWA titles and key items) | 6.11 mm | 36 | 41 | 54 / 62 |
| 60 | 12.22 mm | 72 | 82 | 108 / 123 |

Recommended size tokens (cap height in px, with the arc minutes they give at 70 cm and 80 cm):

| Token | Use | Cap height | Arcmin 70 / 80 cm | Atkinson font px | Inter font px |
|---|---|---|---|---|---|
| `speed` | Speed digits | 120 px (20.4 mm) | 100 / 88 | 180 | 165 |
| `primary` | SOC %, range, gear, next turn distance | 48 px (8.2 mm) | 40 / 35 | 72 | 66 |
| `label` | Units, labels, secondary values on the driving page | 28 px (4.8 mm) | 23 / 20 | 42 | 39 |
| `floor` | Absolute minimum, parked-only pages | 22 px (3.7 mm) | 18 / 16 | 33 | 31 |

Nothing on the driving page goes below `label` (20 arcmin even at 80 cm). The current small captions (for example 12 px cap, which is 10 arcmin at 70 cm) fall below ISO's 12 arcmin minimum.

### 4.3 Typeface

Primary recommendation: Atkinson Hyperlegible Next (Braille Institute). Fallback: B612. Second fallback: Inter.

| Typeface | Why | Licence | On Raspberry Pi OS | Digits |
|---|---|---|---|---|
| Atkinson Hyperlegible Next | Designed by the Braille Institute for maximum character differentiation (0 vs O, 1 vs l vs I); humanist, open apertures, consistent with [2]; variable weight | SIL OFL 1.1 (Google Fonts metadata) | Original Atkinson Hyperlegible is packaged as `fonts-atkinson-hyperlegible` in Debian trixie (not bookworm); the Next version installs by copying the TTF to `~/.local/share/fonts` | Proportional by default; tabular figures via the `tnum` feature |
| B612 | Commissioned by Airbus with ENAC and Université de Toulouse for cockpit displays; design iterated through laboratory and cockpit experiments (Vinot and Athènes, CHI 2012, [20]) | Eclipse Public License 2.0, EDL 1.0 and SIL OFL 1.1 (project README) | `fonts-b612` in Debian bookworm and trixie | Tabular by default (measured); Regular and Bold only |
| Inter | Excellent screen rendering, many weights | SIL OFL 1.1 | `fonts-inter` in Debian bookworm and trixie | `tnum` available |

Use tabular figures for all live numbers (speed, SOC, range) so digits do not shift as values change. Qt 6.7 and later expose OpenType features through `QFont.setFeature`; if the installed PySide6 is older, use B612 for numerals because its digits are already fixed width. Use Regular and Bold (or 500 and 700) only; no Light or Thin weights. None of these three faces has been tested in a driving glance study; the evidence supports their features (open apertures, clear differentiation), not the specific fonts.

### 4.4 Palette (with measured WCAG contrast ratios)

Contrast ratios computed with the WCAG 2 relative-luminance formula. Target: 7:1 or better for every text and semantic colour against its background.

Night theme (default after sunset; negative polarity, low luminance):

| Token | Hex | On background #0E1116 | On surface #1A1F26 |
|---|---|---|---|
| background | #0E1116 | | |
| surface (only where grouping is essential) | #1A1F26 | | |
| text primary | #F5F7FA | 17.6 | 15.4 |
| text secondary | #BAC2CC | 10.5 | 9.2 |
| critical red (text, icons) | #FF857B | 8.0 | 7.0 |
| warning amber | #FFB224 | 10.5 | 9.2 |
| ok green | #3FD68A | 10.1 | 8.8 |
| info blue (navigation, selected) | #80C0FF | 9.8 | 8.6 |
| divider (not for text) | #2E3540 | 1.5 | |

Day theme (default in daylight; positive polarity):

| Token | Hex | On background #F7F8FA | On surface #FFFFFF |
|---|---|---|---|
| background | #F7F8FA | | |
| surface | #FFFFFF | | |
| text primary | #0B0D10 | 18.3 | 19.5 |
| text secondary | #3B4450 | 9.3 | 9.9 |
| critical red | #951B12 | 8.1 | 8.6 |
| warning amber (text) | #753F00 | 8.0 | 8.5 |
| ok green | #0E5A2A | 7.9 | 8.4 |
| info blue | #0947AA | 7.9 | 8.4 |
| divider (not for text) | #D5DAE1 | 1.3 | |

Alert banners (same in both themes, so the meaning never changes with theme):

| Banner | Fill | Text | Contrast |
|---|---|---|---|
| Critical | #A3201A | #FFFFFF | 7.6 |
| Warning | #FFB224 | #0B0D10 | 10.8 |

For comparison, typical neon accents on the night background: neon purple #B026FF 4.1:1, rose gold #B76E79 5.0:1, neon pink #FF10F0 5.9:1, grey caption #6B7280 3.9:1. These are illustrative values for the named colours, not values read from the current code; the point is that saturated neon accents fail 7:1, and the purple and grey caption fail even Google's 4.5:1 minimum.

Other palette rules: one accent (info blue) only; red, amber and green are reserved for meaning and never used for decoration; no gradients, glows or translucency over live values; at night, dim the backlight as well as switching theme, because the after-effect on night vision depends on emitted light [6][7].

### 4.5 Day and night switching

- Automatic switching from an ambient light sensor if one is fitted, otherwise from sunrise and sunset times for Cape Town, with a manual override (the Uber pattern: Automatic, Always on, Always off [23]).
- Field test before committing: in direct Cape Town sun, compare both themes on the actual panel for readability of `label`-size text at 80 cm. If the dark theme reads better in practice on this panel (reflections can change the result), keep dark for both, as Google does [10].

### 4.6 Alert levels

| Level | Examples (Tukzie) | Visual | Sound | Behaviour |
|---|---|---|---|---|
| 3 Critical: act now | BMS cut-off imminent, pack or motor over-temperature, insulation fault, brake fault | Full-width critical banner at the top of the driving page, icon plus 2 to 4 word message, displaces other content | Distinct repeating tone | Stays until the condition clears; cannot be dismissed while the condition exists (R121 pattern [16]); multimodal per [5] |
| 2 Warning: act soon | SOC below 15 %, temperature rising, charger fault | Warning banner below the speed, icon plus words | Single chime on first appearance | Can be acknowledged; shrinks to a status icon, returns if worse |
| 1 Advisory | Range estimate updated, trip logged, Wi-Fi lost | Small icon or secondary text in the status strip | None | Self-clearing |
| 0 Normal | Ready, charging | Neutral text; green only for "Ready" or "Charging" | None | |

Each alert uses colour plus icon plus words plus a fixed position, never colour alone (rule 13, [32]). Keep the message vocabulary small and consistent so the driver recognises it rather than reads it.

### 4.7 What goes on which page

Driving page (shown whenever the vehicle is not parked; the only page available while moving):

1. Speed (largest item, top, nearest the driver's line of sight).
2. Active alerts (banner area directly under or above the speed, empty when there is nothing to say).
3. Battery: SOC % and estimated range in km, one bar.
4. Drive state: gear or drive mode and "Ready".
5. Turn indicators and hazard status (mirroring the physical switch).
6. Next turn instruction and distance, only if navigation is running.
7. Clock (small).

That is at most about six information groups, each readable in one fixation. There is no published hard limit on items per glance; this number is an engineering judgement based on the 2 s glance rule [1] and the "no clutter" guidance [12].

Secondary pages (parked only): trip analytics, energy graphs, efficiency comparisons, charging history, diagnostics, settings, CAN and sensor detail. See Section 5.

### 4.8 Touch targets

| Item | Size | Pixels on this panel |
|---|---|---|
| Absolute minimum (Euro NCAP) | 10 x 10 mm, 4 mm gap | 59 x 59 px, 24 px gap |
| Google minimum (76 dp) | about 12 x 12 mm, 23 dp gap | 71 x 71 px |
| Recommended for any control usable while moving | 17.5 x 17.5 mm or larger [14] | 104 x 104 px or larger |
| Recommended gap | at least 4 mm | 24 px or more |

A tuk-tuk vibrates more than a car and the driver may wear gloves, so 104 px is the recommended minimum for anything touchable while moving, and in practice the driving page should need no touch at all. Avoid swipe gestures, sliders and long-press while moving. Respond to every touch within 0.25 s [1].

### 4.9 What to remove from the current UI

| Remove | Why | Source |
|---|---|---|
| Neon palettes (Electric Blue, Neon Purple, Neon Pink, Rose Gold and similar) and theme pickers that change semantic colours | Several fail 4.5:1; saturated blue is specifically discouraged; colour meaning must stay fixed | [5][8][10] |
| Glows, outer shadows, gradients behind numbers | Reduce effective contrast and edge sharpness; "unnecessary visual embellishments" | [12] |
| Decorative motion (pulsing, animated backgrounds, rolling digits) | NHTSA lock-out of non-driving images and auto-scrolling; Android limits animation to 1 fps while moving | [1][11] |
| Small, dim captions (grey on dark, light weights) | Below 12 to 20 arcmin and below 7:1 | [2][5] |
| Many cards and panels on the driving page | Each card border and background adds visual search time; group with spacing instead | [12][21] |
| Square or techno display fonts | Square grotesque increased glance time versus humanist | [2] |
| Touch-only access to indicators, hazards, horn, drive mode | Euro NCAP requires physical controls for these | [13] |

## 5. Secondary screens used only when parked (analytics, graphs, comparisons)

### 5.1 How production systems handle them

- Android Automotive: parked = unrestricted; idling (not in Park, speed zero) = no video and no configuration screens; moving = fully restricted, which includes limiting the number of items a user can browse through in one task and the depth of navigation [11].
- Apple CarPlay: the car can limit list length and keyboard display; apps must read the current maximum item count at runtime [12].
- Tesla: games locked while moving after the NHTSA probe [26].
- NHTSA: stopped at a light is still "driving"; lock-out applies until Park or the parking-brake-plus-neutral condition [1].

### 5.2 Lock rule for Tukzie

- Unlocked: drive state is Park or Neutral with parking brake engaged and speed 0 (adapt to whatever signals the Tukzie controller exposes). Speed zero alone is not enough [1].
- On leaving the parked state: immediately return to the driving page, keep the carousel position in memory for next time, and show no transition animation longer than about 300 ms (engineering judgement).
- While moving, the analytics pages are not reachable at all. If a summary is wanted while moving, show at most one static, read-only line on the driving page (for example trip energy in Wh/km) at `label` size or larger.

### 5.3 Recommended structure for the vertical swipe carousel

| Rule | Recommendation | Basis |
|---|---|---|
| One card per screen | Each card fills the content area (full width, about 640 to 700 px tall); vertical snap paging, never free scrolling | Removes partial cards and reading mid-scroll; fits the "limit content" idea [11] |
| One question per card | Card title is a plain question or label ("Energy this trip"), one headline number at `primary` size, one chart, one line of context | Glanceable even when parked, since drivers check between jobs |
| Fixed order, shallow depth | 5 to 7 cards in a fixed order; no drill-down deeper than one level; a page indicator (dots or "3 / 6") on the right edge | Android limits content depth and item count [11] |
| Charts | Bar or line only; at most 2 series; direct labels instead of legends; axis labels at `floor` size or larger; colours from the palette, with the second series distinguished by pattern or label as well as colour | Never colour alone [32]; contrast [5][8] |
| Comparisons | Show the comparison as a number with a word ("12 % better than last week"), then the chart | Reading a number is quicker than reading a chart |
| Controls | Swipe up and down plus large up and down buttons (104 px) for gloved hands; no horizontal swipes inside cards | Touch target research [14] |
| Exit | A large "Drive" button always visible; also automatic exit on leaving Park | [1] |
| Motion | Snap animation under 300 ms, no animated chart drawing | Decorative motion lock-out [1][11] |

Suggested card order: 1 Trip summary (distance, energy, Wh/km). 2 Energy over the trip (line). 3 Efficiency versus previous days (bar). 4 Battery health and temperature history. 5 Charging sessions. 6 Diagnostics and alerts log. 7 Settings (last, so it is never reached by accident).

## 6. Sources

Status tags: [PDF saved] file is in `papers/`; [paywalled] not downloaded, DOI or URL given; [web page] read online, not a PDF.

1. National Highway Traffic Safety Administration (2013). Visual-Manual NHTSA Driver Distraction Guidelines for In-Vehicle Electronic Devices. Federal Register 78(81), 24818-24890, Docket NHTSA-2010-0053. https://www.govinfo.gov/content/pkg/FR-2013-04-26/pdf/2013-09883.pdf. File: `2013_NHTSA_visual-manual-distraction-guidelines.pdf` [PDF saved]
2. Reimer, B., Mehler, B., Dobres, J., Coughlin, J. F., Matteson, S., Gould, D., Chahine, N. and Levantovsky, V. (2014). Assessing the impact of typeface design in a text-rich automotive user interface. Ergonomics 57(11), 1643-1658. https://doi.org/10.1080/00140139.2014.940000 (open access via MIT DSpace https://dspace.mit.edu/handle/1721.1/96509). File: `2014_Reimer-MIT-AgeLab_typeface-design-automotive-ui.pdf` [PDF saved]. Also the secondary source for the ISO 15008 arc-minute ratings.
3. You, F., Yang, Y.-F., Fu, M.-T., Zhang, J. and Wang, J.-M. (2021). Design Guidelines for the Size and Length of Chinese Characters Displayed in the Intelligent Vehicle's Central Console Interface. Information 12(5), 213. https://doi.org/10.3390/info12050213. File: `2021_You-Tongji_chinese-character-size-central-console.pdf` [PDF saved]. Secondary source for ISO 15008 (20 arcmin recommended, 16 acceptable).
4. ISO 15008:2017. Road vehicles: Ergonomic aspects of transport information and control systems: Specifications and test procedures for in-vehicle visual presentation. International Organization for Standardization. https://www.iso.org/standard/62784.html [paywalled]. Figures quoted only via [2] and [3].
5. Campbell, J. L., Carney, C. and Kantowitz, B. H. (1998). Human Factors Design Guidelines for Advanced Traveler Information Systems (ATIS) and Commercial Vehicle Operations (CVO). FHWA-RD-98-057, US Federal Highway Administration. Chapter 3: https://www.fhwa.dot.gov/publications/research/safety/98057/ch03.cfm; Chapter 7: https://www.fhwa.dot.gov/publications/research/safety/98057/ch07.cfm [web page]
6. Piepenbrock, C. (2014). Ergonomische Gestaltung digitaler Anzeigen für jüngere und ältere Erwachsene: Optimierung der Lesbarkeit durch eine positiv polare Textdarstellung. Doctoral dissertation, Heinrich-Heine-Universität Düsseldorf (includes the English-language papers by Piepenbrock, Mayr and Buchner). https://docserv.uni-duesseldorf.de/servlets/DerivateServlet/Derivate-31413. File: `2014_Piepenbrock-HHU-Duesseldorf_display-polarity-dissertation.pdf` [PDF saved]
7. Mayr, S. and Buchner, A. (2010). After-effects of TFT-LCD display polarity and display colour on the detection of low-contrast objects. Ergonomics 53(7), 914-925. https://doi.org/10.1080/00140139.2010.484508 [paywalled]. Findings taken from the abstract (SWOV record https://swov.nl/en/publicatie/after-effects-tft-lcd-display-polarity-and-display-colour-detection-low-contrast-objects) and from [6].
8. Google. Android for Cars design: Visual principles. https://developers.google.com/cars/design/design-foundations/visual-principles [web page]
9. Google. Android Auto design system: Sizing. https://developers.google.com/cars/design/android-auto/design-system/sizing [web page]
10. Google. Android Auto design system: Color, https://developers.google.com/cars/design/android-auto/design-system/color ; Android Automotive OS design system: Color, https://developers.google.com/cars/design/automotive-os/design-system/color [web page]
11. Android Open Source Project. Car User Experience Restrictions, https://source.android.com/docs/automotive/driver_distraction/car_uxr ; and API reference CarUxRestrictions, https://developer.android.com/reference/android/car/drivingstate/CarUxRestrictions [web page]
12. Apple. Human Interface Guidelines: CarPlay (last updated 2 May 2023), https://developer.apple.com/design/human-interface-guidelines/carplay ; CarPlay framework: CPListTemplate.maximumItemCount and CPLimitableUserInterface, https://developer.apple.com/documentation/carplay [web page]
13. Euro NCAP (2026). Safe Driving: Driver Engagement Protocol, Version 1.2, July 2026 (implementation January 2026). https://cdn.euroncap.com/cars/assets/Euro_NCAP_Protocol_Safe_Driving_Driver_Engagement_v1_2_ebce03a443.pdf. File: `2026_EuroNCAP_safe-driving-driver-engagement-protocol-v1-2.pdf` [PDF saved]
14. Kim, H., Kwon, S., Heo, J., Lee, H. and Chung, M. K. (2014). The effect of touch-key size on the usability of In-Vehicle Information Systems and driving safety during simulated driving. Applied Ergonomics 45(3), 379-388. https://doi.org/10.1016/j.apergo.2013.05.006 [paywalled]. Result (benefit levels off at 17.5 mm) taken from the abstract.
15. Kim, H., Kwon, S., Heo, J., Lee, H. and Chung, M. K. (2011). Effect of Touch-key Sizes on Usability of Driver Information Systems and Driving Safety. Journal of the Korean Institute of Industrial Engineers 37(1), 30-40 (in Korean, English abstract). https://doi.org/10.7232/jkiie.2011.37.1.030. File: `2011_Kim-POSTECH_touch-key-size-driver-information-systems.pdf` [PDF saved]
16. UNECE (2010, with amendments). UN Regulation No. 121: Uniform provisions concerning the approval of vehicles with regard to the location and identification of hand controls, tell-tales and indicators. Copy hosted by Japan MLIT: https://www.mlit.go.jp/jidosha/un/UN_R121.pdf. File: `2010_UNECE_R121-controls-tell-tales-indicators.pdf` [PDF saved]
17. Strayer, D. L., Cooper, J. M., Goethe, R. M., McCarty, M. M., Getty, D. J. and Biondi, F. (2017). Visual and Cognitive Demands of Using In-Vehicle Infotainment Systems. AAA Foundation for Traffic Safety. https://aaafoundation.org/visual-cognitive-demands-using-vehicle-information-systems/. File: `2017_Strayer-AAAFTS_visual-cognitive-demands-infotainment.pdf` [PDF saved]
18. Ramnath, R., Kinnear, N., Chowdhury, S. and Hyatt, T. (2020). Interacting with Android Auto and Apple CarPlay when driving: The effect on driver performance. TRL Published Project Report PPR948, TRL and IAM RoadSmart. Record: https://trid.trb.org/View/1694794 ; publisher page https://trl.co.uk/publications/interacting-with-android-auto-and-apple-carplay-when-driving ; press summary: European Transport Safety Council, 18 March 2020, https://etsc.eu/apple-carplay-and-android-auto-infotainment-systems-weaken-reactions-more-than-alcohol-and-cannabis/ [web page]. Full report not downloaded (publisher page did not serve the PDF).
19. Vi Bilägare (2022). Physical buttons outperform touchscreens in new cars, test finds. https://www.vibilagare.se/english/physical-buttons-outperform-touchscreens-new-cars-test-finds [web page]
20. Vinot, J.-L. and Athènes, S. (2012). Legible, are you sure? An experimentation-based typographical design in safety-critical context. Proceedings of CHI 2012, 2287-2296. https://doi.org/10.1145/2207676.2208387 ; open copy listed at https://enac.hal.science/hal-01022511 (blocked to automated download) [paywalled]. B612 project: https://github.com/polarsys/b612 [web page]
21. Polestar (2019). Journal 12.2 (23 January 2019), on the Polestar 2 user interface. https://www.polestar.com/global/news/journal-12-2/ [web page]
22. Choksi, M. and Leung, W. (2017). A New Navigation Experience for Drivers. Uber Newsroom, 15 March 2017. https://www.uber.com/newsroom/a-new-navigation-experience-for-drivers/ [web page]. 22a: Uber Newsroom (2018). Introducing the new Driver app. https://www.uber.com/us/en/newsroom/new-driver-app/ [web page]
23. Uber Help. Uber Driver app navigation features. https://help.uber.com/en/driving-and-delivering/article/uber-driver-app-navigation-features?nodeId=357c291a-9b6e-45e9-9614-aea820f089ce [web page]
24. Uber Design (Medium). Uber Navigation: Designing for drivers. https://medium.com/uber-design/uber-navigation-f662e7611f3 [web page, blocked; content known only from search-engine excerpts, partly verified]
25. Hughes, J. / The Drive (2017). Tesla Model 3 touchscreen design. Fortune, 10 August 2017. https://fortune.com/2017/08/10/tesla-model-3-touchscreen-design [web page]
26. Carscoops (2023). Game over: NHTSA closes investigation into Tesla's in-car gaming feature, 30 May 2023. https://www.carscoops.com/2023/05/game-over-nhtsa-closes-investigation-into-teslas-in-car-gaming-feature/ [web page]
27. Anderson, B. (2023). VW to bring back buttons and some of the missing charm in its interiors. Carscoops, 21 December 2023. https://www.carscoops.com/2023/12/vw-to-bring-back-buttons-and-some-of-the-missing-charm-in-its-interiors/ [web page]
28. Parkers. BYD Atto 3 review: interior, tech and comfort. https://parkers.co.uk/byd/atto-3/review/interior [web page]
29. InsideEVs (2024). Rivian software artwork: Jeff Hammoud interview. https://insideevs.com/news/742830/rivian-software-artwork-hammoud-interview/ ; Epic Games, Rivian brings adventurous spirit to new display UI powered by Unreal Engine, https://www.unrealengine.com/en-US/spotlights/rivian-brings-adventurous-spirit-to-new-display-ui-powered-by-unreal-engine [web page, blocked; partly verified]
30. Uber Newsroom NZ (2018). Introducing Speed Alerts, 23 November 2018. https://www.uber.com/en-NZ/newsroom/speedalertsnz [web page]
31. Connecting Africa (2022). Bolt introduces additional safety features on driver's app, 9 September 2022. https://www.connectingafrica.com/emerging-technology/bolt-introduces-additional-safety-features-on-driver-s-app [web page]
32. Almustanyir, A. (2025). A Global Perspective of Color Vision Deficiency: Awareness, Diagnosis, and Lived Experiences. Healthcare 13(16), 2031. https://doi.org/10.3390/healthcare13162031 [web page; open access, PDF download blocked]
33. Song, J. (2020). Didi, BYD unveil customized EV for ride-hailing. KrASIA, 17 November 2020. https://kr-asia.com/didi-byd-unveil-customized-ev-for-ride-hailing [web page]
34. Gogoro (2024). Gogoro Unveils New Flagship Smartscooter, Pulse, 30 January 2024. https://www.gogoro.com/news/gogoro-pulse/ [web page]
35. Font licences and packages: Google Fonts metadata for Atkinson Hyperlegible and Inter (OFL), https://github.com/google/fonts/tree/main/ofl ; Debian packages `fonts-inter`, `fonts-b612` (bookworm and trixie), `fonts-atkinson-hyperlegible` (trixie), https://packages.debian.org [web page]

## 7. Not verified or open items

- ISO 15008 contrast minimums by lighting condition (5:1 night, 3:1 day, 2:1 sunlight): not traced to a citable source.
- ISO 2575 colour meanings: only the general convention via FHWA [5] and R121 [16]; the ISO text itself was not read.
- ISO 15005 and ISO 16673: not accessed; NHTSA notes the 1.5 s occlusion viewing interval comes from ISO 16673:2007 [1].
- EU European Statement of Principles on HMI (Commission Recommendation 2008/653/EC): EUR-Lex blocked automated access, so it is not cited.
- Apple CarPlay "7:1 preferred contrast" and "44 pt targets" appear in third-party summaries but not in the current Apple CarPlay page; not used.
- Uber night mode design process [24] and Rivian quotes [29]: from search-engine excerpts only.
- Bolt Driver app theme and design rationale: nothing credible found.
- Electric three-wheeler dashboards (Bajaj, Piaggio, Ola, Ather legibility claims): no published design rationale or independent measurement found.
- Sunlight readability of the actual Tukzie panel: needs a measurement (luminance meter or at least a side-by-side outdoor test).
