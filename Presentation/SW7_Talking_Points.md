# Final presentation: talking points

Generated from the speaker notes by Presentation/source/build_deck.js; edit the notes there, not here.

13 slides, 10 minutes plus 5 minutes of questions. 1340 words in total, about 9.6 minutes at 140 words a minute.

## Slide 1: Title (52 words, about 22 s)

Good morning. I'm Samson Okuthe. My project gives the TUKZIE electric cargo trike embedded telemetry: it measures how the trike rides, warns the driver of hazards on the dashboard it already has, and keeps its data when coverage drops. I was supervised by Associate Professor Simon Winberg, with Sampath Jayalath as co-supervisor.

## Slide 2: Why this matters (88 words, about 38 s)

Electric cargo trikes make sense for freight in African cities: in Dar es Salaam an electric cargo tricycle cost 45.5 percent less per kilometre to run than a motorcycle, and 86 percent less than a light car. But anything that takes the driver's eyes off the road is a risk; NHTSA guidance wants glances away from the road to mostly last two seconds or less. So the problem is to put edge telemetry and short, safety-only alerts on a low-cost trike, and to measure whether each part works. 

## Slide 3: Aim, research questions and approach (74 words, about 32 s)

The aim is on the slide. Four research questions follow from it: how accurately and repeatably the ride can be measured; how alerts should appear with the least distraction; what latency, loss and recovery the data chain achieves; and which features separate road from powertrain vibration. The approach was a V-model: thirteen requirements with criteria fixed before each test, every part tested on the bench, then on the vehicle on 19 and 27 October.

## Slide 4: The system as driven on 27 October (114 words, about 49 s)

This is the system as driven on 27 October. It has two sides joined by one Ethernet cable, which also shares the clock. At the front, a Raspberry Pi 5 behind the display runs the dashboard, the front camera and detector, three time-of-flight sensors and the front IMU node; a phone streams its GNSS for speed. At the rear, a Raspberry Pi 4 beside the battery runs the rear camera and reads two boards: the rear IMU node, and the telemetry unit, which reads the battery, GNSS and LTE and logs to flash. So there are three ESP32-S3 boards. Run from a portable power station, the whole system drew 27 watts at its output.

## Slide 5: Deterministic acquisition: a 33 to 44 ms gap found and removed (109 words, about 47 s)

Ride measurement needs a fixed sample rate. Under FreeRTOS the IMU task runs at top priority on a 5 millisecond period and never blocks: if its queue is full, the sample is dropped and counted. Counting exposed the one timing fault. Every flash write paused reading for 33 to 44 milliseconds, the spikes in this plot. Buffering made the pauses rarer, not shorter. The fix was to take logging off the IMU nodes: on the vehicle they held 200 hertz with no interval over 5.2 milliseconds. On the road the front node lost nothing in 1.8 million samples; the rear lost 0.08 percent in transport, none at the node.

## Slide 6: Fault investigations: symptom, test, cause, fix (108 words, about 46 s)

Because each stage was tested before the next, each fault could be traced to one change. The one that mattered most is power. The Pi 4 kept throttling and restarting. Logging its power flags every two seconds showed under-voltage starting fourteen seconds after the telemetry unit's modem came up on its USB port. Moved off, it went from three restarts in twenty minutes to none in four hours. The others: a task stall hidden behind a healthy-looking rate, a dead sensor connection that led to the third board, a flash-mode boot loop, a battery checksum off by three, and invalid JSON found only by reading the log back.

## Slide 7: Telemetry: log first, then store and forward (115 words, about 49 s)

Every record is written to flash whatever the coverage, then sent over LTE and replayed when the link returns. On the bench I switched the radio off for ten minutes. The unit reconnected 5.2 seconds after it came back, cleared its 60-record backlog in about 38 seconds, and the database held 112 of 112 records, none missing or doubled. On the road the wired link to the Pi carried 4,196 of 4,201 records, 99.9 percent, against 62 percent over USB on the first session. Over LTE 153 records arrived, 116 of them replays, with a median delay of 0.44 seconds; but only nine records carry that figure, and from 11:51 the link did not reconnect.

## Slide 8: Hazard detection on the road: front and rear (113 words, about 48 s)

Each camera runs a pretrained 8-bit SSD-MobileNet detector. On the road the front, on the Pi 5, took a median of 68 milliseconds from readout to result at 23.3 frames per second; the rear, on the Pi 4, 103 milliseconds at 12.1. An alert is raised after three frames and cleared after five, and no frame is ever stored. Distance bands do not say whether something is closing, so the system also estimates time to contact from how fast a box grows; it is within 2 percent in 40 synthetic tests but has not met a real approach. No forward video was kept, so how many road alerts were correct is still unknown.

## Slide 9: The existing dashboard: live alerts, honest legibility (120 words, about 51 s)

RQ2 lands on the dashboard the team already runs, here on the vehicle. It shows only live data, never a simulated value, and an immediate hazard appears as a banner over every page. Glance time needs a participant and an ethics amendment, so it was not tested; but legibility needs neither, so I measured it at the driver's eye distance of 0.62 metres. The speed digits subtend 94 arc minutes, far above the 20 that ISO 15008 recommends. The alert banner subtends 10, below even its minimum of 12. So the hierarchy is inverted: the warnings must be enlarged before any glance study. Spoken commands work offline, 15 to 18 of 18 on the bench, but no driver was tested.

## Slide 10: Road test, 27 October: repeatable per pass, not per place (118 words, about 51 s)

This is the main road result. On a smooth loop at 10 kilometres an hour, five passes gave a weighted acceleration, a w, that varied by 5.0 percent at the rear and 5.3 at the front, inside the 10 percent criterion. On a rougher strip it read about twice as high at the same speed, so the measurement responds to the road. But aligned by position in 8 metre cells, the passes did not agree place by place: an ICC of 0.16, at most 0.32 in the sensitivity checks, against 0.75. With one-second phone positions I cannot separate this from the line each lap took. The speed index also rose with speed, so it is not speed-invariant here.

## Slide 11: Powertrain against road: the road dominates (110 words, about 47 s)

RQ4 asks what is road and what is powertrain. With the drive wheel raised on stands, the motor shook the body between about 40 and 70 hertz, with the same lines at the front as at the rear, so the front sensor does not escape it. On the road, those lines held only 0.9 to 3.1 percent of the energy in powered passes, while 65 to 84 percent lay between 4 and 8 hertz, the body's response to the road. A coasting pass gave the same reading as a powered one, 1.80 against 1.78. So at these low speeds the road dominates; at higher power the motor's share would grow.

## Slide 12: Conclusions: each question answered in part (114 words, about 49 s)

So, honestly, each question is answered in part. RQ1: the instrument is verified on the bench, and on the road it repeats over whole passes but not yet place by place. RQ2: the alerts are built and live-only, but the warning text is too small and glance time was not measured. RQ3: on the bench every record survived a ten-minute outage; on the road the wired link carried 99.9 percent, but LTE latency rests on nine records. RQ4: at these speeds the road dominates. Of thirteen requirements, five are met on the bench, seven partly and one, glance time, was not tested. On the vehicle R1 was met at the front, R2 was not.

## Slide 13: Contribution and next steps (105 words, about 45 s)

The contribution is an integrated low-cost architecture, a measured account of its timing and loss, and road evidence that the ride measurement repeats over whole passes. Four steps would make it dependable. First, a regulated supply for the telemetry unit, never a Pi's USB port. Second, fix the LTE reconnection and measure latency on the road. Third, marked sections with side video and three passes per speed, for a place-by-place ICC. Fourth, validate the fusion and time to contact against a flat target, a real approaching car and labelled video. Videos of the road test are at tuksense.site. Thank you; I'm happy to take questions.
