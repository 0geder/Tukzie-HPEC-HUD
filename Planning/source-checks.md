# Source checks

Every external source used to check a value in the report is downloaded, filed under References/Papers and listed
here with where it came from, its SHA-256 (first 16 hex digits), what was taken from it and the result. Newest last.

## 2026-10-24: ISO 2631-1 Wk weighting filter (BenchTest/analysis/dsp.py)

Claim checked: the filter's band-limiting, transition and step parameters, and its gain at the one-third-octave
frequencies. The standard itself (ISO 2631-1:1997) is paywalled and was not consulted; the check is against
published derivations of it. Files in References/Papers/IMU-Based Ride Smoothness and Road Roughness, downloaded
24 Oct 2026.

| File | Source URL | Bytes | SHA-256 | Used for |
|---|---|---|---|---|
| Rimell_Mansfield_2007_Digital_filters_frequency_weightings_vibration_IndHealth45-512.pdf | https://www.jstage.jst.go.jp/article/indhealth/45/4/45_4_512/_pdf | 93,464 | 7b28f425bffaec32 | Table 3, Wk row: f1 0.4 Hz, Q1 1/sqrt2, f2 100 Hz, Q2 1/sqrt2, f3 = f4 12.5 Hz, Q4 0.63, f5 2.37 Hz, Q5 0.91, f6 3.3 Hz, Q6 0.91 |
| Rimell_Mansfield_2010_Erratum_IndHealth48-129.pdf | https://www.jniosh.johas.go.jp/en/indu_hel/doc/IH_48_1_129.pdf | 20,582 | 115e9dbca6dd3a11 | Corrects Equation 4 (the Wk step term) of the 2007 paper |
| Rimell_Mansfield_2010_Corrigendum_IndHealth48-743.pdf | https://www.jniosh.johas.go.jp/en/indu_hel/doc/IH_48_5_743.pdf | 429,339 | fedf27bac7aab6ae | Corrects Equation 4 again and Tables 5 and 8 (BS 6841 Wb gain, Wh equations); Wk parameters unaffected |
| Virtins_2024_Frequency_weightings_for_sound_and_vibration.pdf | https://virtins.com/doc/Frequency-Weightings-for-Sound-and-Vibration-Perceived-by-Humans-using-Multi-Instrument.pdf | 1,634,259 | 7c912b58b881c255 | Wk parameter table with f6 3.35 Hz, Q6 0.91, and Wk at one-third-octave frequencies 0.1 to 400 Hz |

Result: the code's parameters equal Rimell and Mansfield's Table 3 except f6 (code 3.35 Hz, paper 3.3 Hz); with 3.35 Hz
the gain matches the Virtins table within 0.005 dB at all 37 frequencies (up to 0.27 dB off with 3.3 Hz), so 3.3 is
read as rounded. The code's Equation 4 form matches the corrected form in the erratum and corrigendum. Tests:
BenchTest/analysis/tests/test_dsp.py (37 Virtins values within 0.006 dB; parameters against the paper; the f6 check).
Report: citations rimell2007, rimell2010corr and virtins2024 (Method 3.6, Appendix J).
