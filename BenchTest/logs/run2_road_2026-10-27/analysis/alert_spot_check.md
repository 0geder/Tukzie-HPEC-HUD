# Alert spot check against the dashboard screen record, 27 October 2026

Done on 17 November 2026, after the report was submitted. Not in the report; present it as later work.

## What was checked

The Pi 5 saved the dashboard screen every 2 s (sw7-screens.service, lab notebook 22 Oct 16:00). From 11:30 to 12:40 there are
2,051 frames; 808 show the Surroundings page, which puts the live camera view beside the hazard list the driver saw
(602 front, 206 rear). An evenly spaced sample of 60 was taken (alert_spot_check_sample.py): 40 where the alert log had an
active alert and 20 where it had none, front and rear. Each frame was judged by eye: is each listed object really in the view,
is the class right, and is anything visible that should have been listed. Labels: alert_spot_check_labels.csv.

The log-based state did not always match the screen (frames 48, 49 and 53 to 58 showed hazards where the reconstructed log
state had none), so every frame was judged against the hazard list shown on the screen, not the log.

## Result

| | Frames | Result |
|---|---|---|
| Hazards shown | 48 (26 front, 22 rear) | Headline object real in 47; class right in 46 |
| Clear shown | 12 | 11 truly clear; 1 possible miss (tractor cut off at the image edge, frame 42) |

Errors seen:
- one false person on an empty track (frame 58, "person 22.3 m left", grey, shown as the headline number);
- distant "person" entries at 22 to 41 m with no person visible, listed grey (low priority) in 5 further frames;
- the tractor shown as "car" once (frame 17; as "truck" otherwise, and COCO has no tractor class);
- one false escalation to immediate: "truck 0.27 m ahead" (frame 22), the ToF range fused to a tractor several metres away;
- a parked bus seen side-on listed at 3.5 to 4.6 m (10 frames); it looks much further, so the box-width distance is likely
  underestimated for side-on vehicles (not measured).

## Limits (say these with the numbers)

- One rater (the assistant, by eye), no second check; not independent video: the camera view is the system's own camera.
- Frames are strongly correlated: the same parked bus, tractor and people standing behind the parked trike recur. The
  effective sample is a handful of scenes, mostly stationary objects at low speed.
- One frame per 2 s, Surroundings page only, so most alerts are not covered and recall cannot be estimated.
- The frames contain people (mostly legs and bodies, small faces in a few). Do not show them without blurring.

So the honest claim is: on a sample of 60 screen frames, the objects the driver was shown were real in 47 of 48, with one
false distant person, one wrong class and one false immediate escalation; distance on side-on vehicles looks unreliable.
Precision and recall over the drive still need independent video.
