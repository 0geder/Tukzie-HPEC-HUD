# ML and the ethics application: position and required actions

Written 2026-09-19, prompted by the ethics application's ML clause.

## The clause

> "At present, machine learning (ML) is not planned for use in this version
> (as in first version) of this proposed system. However, should the student
> doing project be making good headway and consider the baseline system is
> sufficiently progress to merit experimenting with ML, then a revised ethics
> application will be prepared and submitted."

Two obligations follow: ML is out of scope for version one, and any move to
experiment with ML requires a **revised application submitted first** — not
retrospectively.

## Audit: what in this project is actually ML

Checked the whole repository for model artefacts and ML libraries.

**Is ML — exactly one component:**
- `CameraDetection/detect.tflite` — a quantised TensorFlow Lite
  SSD-MobileNet-v1 neural network (COCO-pretrained), with
  `hazard_detector.py` running inference against it.

**Is NOT ML, despite sometimes being described loosely as "detection":**
- Ride characterisation (`computeRideFeatures`) — RMS, standard deviation,
  peak-to-peak, crest factor, mean absolute jerk, threshold crossings. All
  classical time-domain signal processing. Zero learned parameters.
- The bench classifier and dashboard event labelling — fixed numeric
  thresholds, hand-set, not learned from data.
- The research pipeline's relevance scoring — keyword overlap, not a model.

This distinction matters and should be stated plainly in the report, because
"detection" and "classification" in the ride-characterisation sections could
otherwise be misread as ML by an examiner or ethics reviewer.

## Current factual status of the ML component

Written, committed, and documented — but **never executed against live
camera data**. No inference has been run on the vehicle, no data collected
through it, no human subjects imaged by it. Writing code that would use a
pretrained model is not the same act as experimenting with ML on the
platform, but the gap is narrow enough that it should be closed
deliberately rather than left ambiguous.

## Execution prompt

> Bring the project into unambiguous alignment with the ethics application's
> ML clause. Specifically:
>
> 1. Decide and record one of two positions, explicitly, in the report:
>    **(a) ML excluded from version one** — the hazard detector is retained
>    in the repository as prepared-but-unused future work, is not run against
>    live camera data, and produces no results in this thesis; or
>    **(b) ML included** — a revised ethics application is prepared and
>    submitted, and *approved*, before any inference is run on or near the
>    vehicle.
>    Do not leave the position implicit. An examiner reading the Methodology
>    chapter alongside the ethics application must be able to see which one
>    applies without inferring it.
>
> 2. Amend the hazard-detection section of `Methodology.tex` to state the
>    ethics position directly, alongside the existing honest note that the
>    component has not been run. The section currently describes a scope
>    extension without reference to the ethics constraint, which reads as
>    though ML is simply part of version one.
>
> 3. State plainly, where ride characterisation is described, that its
>    detection and classification are threshold-based signal processing with
>    no learned model, so that the ML boundary in this project is
>    unambiguous.
>
> 4. If position (b) is chosen, the revised application should cover what the
>    camera actually captures: a forward-facing road scene in a public
>    environment, which may incidentally image pedestrians and other road
>    users. Address retention, whether frames are stored or only inference
>    results, and how incidentally-captured people are handled. Note that the
>    model is pretrained on a public dataset, so no training data is
>    collected by this project — which materially narrows what the amendment
>    has to justify.
>
> 5. Check that no other project component has drifted into ML without being
>    noticed, and re-run that check if new functionality is added.

## Recommendation

Take position (a) for now. The hazard detector has never been run, the
thesis has no results depending on it, and the four chapters that are
actually empty (Results, Discussion, Conclusions, Recommendations) are
gated on the ride-characterisation field test, which involves no ML
whatsoever. Filing an amendment costs time on the critical path and buys
nothing the thesis currently needs.

Position (b) becomes worth it only if the field test is complete and there
is genuine time left to do the camera work properly — which is precisely the
condition the ethics clause itself describes ("sufficiently progressed to
merit experimenting with ML").
