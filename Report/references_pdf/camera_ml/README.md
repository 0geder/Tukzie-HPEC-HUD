# Camera and ML reading library for SW-7 (TUKZIE hazard awareness)

This folder holds the papers behind the camera side of the project: a pretrained object detector running on a Raspberry Pi 4 camera to warn the rider of the TUKZIE electric cargo trike about hazards, tested in a university parking lot and around campus.

Every arXiv paper below was checked against its arXiv abstract page and the arXiv API (title and first author), and every PDF was checked to start with %PDF and to be larger than 100 KB. Publisher DOIs were checked on Crossref (the registry behind doi.org). The summaries are written only from each paper's abstract.

## Start here

If you are new to computer vision, read these four first. Together they explain what the current model is and why it runs on a Pi.

1. lin2014_coco.pdf: the COCO dataset. This is what the current model learned from, and it fixes the list of everyday object types the model can recognise (person, car, bicycle, and so on). Check the label map shipped with the model for the exact class list.
2. howard2017_mobilenets.pdf: MobileNet, the small, fast "backbone" network that turns a camera frame into features.
3. liu2016_ssd.pdf: SSD, the detector design that sits on top of MobileNet and outputs boxes and class labels in one pass.
4. jacob2018_quantization.pdf: why the model uses 8-bit integers instead of floating point, which is what makes it fast enough on a Pi CPU.

After that, a sensible order is: sandler2018_mobilenetv2 (SSDLite), alqahtani2024_edge_benchmark (real Pi 4 numbers), redmon2016_yolo and terven2023_yolo_review (the YOLO family), tan2020_efficientdet (upgrade option), yosinski2014_transferable (fine-tuning), then the task-specific papers (distance, cones, road damage, Cityscapes, colour thresholding).

## Paper table

| File | Citation | arXiv ID / DOI | What it explains for this project | Status |
|---|---|---|---|---|
| liu2016_ssd.pdf | W. Liu, D. Anguelov, D. Erhan, C. Szegedy, S. Reed, C.-Y. Fu, A. C. Berg, "SSD: Single Shot MultiBox Detector", ECCV 2016 (LNCS), pp. 21-37, 2016 | arXiv 1512.02325; DOI 10.1007/978-3-319-46448-0_2 | The detector architecture the current model uses | Downloaded |
| howard2017_mobilenets.pdf | A. G. Howard, M. Zhu, B. Chen, D. Kalenichenko, W. Wang, T. Weyand, M. Andreetto, H. Adam, "MobileNets: Efficient Convolutional Neural Networks for Mobile Vision Applications", arXiv preprint, 2017 | arXiv 1704.04861 | The lightweight backbone the current model uses | Downloaded |
| lin2014_coco.pdf | T.-Y. Lin, M. Maire, S. Belongie, J. Hays, P. Perona, D. Ramanan, P. Dollar, C. L. Zitnick, "Microsoft COCO: Common Objects in Context", ECCV 2014 (LNCS), pp. 740-755, 2014 | arXiv 1405.0312; DOI 10.1007/978-3-319-10602-1_48 | The dataset the current model was trained on, and so the classes it knows | Downloaded |
| jacob2018_quantization.pdf | B. Jacob, S. Kligys, B. Chen, M. Zhu, M. Tang, A. Howard, H. Adam, D. Kalenichenko, "Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference", CVPR 2018, pp. 2704-2713 | arXiv 1712.05877; DOI 10.1109/CVPR.2018.00286 | Why the model is 8-bit quantized and what accuracy that costs | Downloaded |
| sandler2018_mobilenetv2.pdf | M. Sandler, A. Howard, M. Zhu, A. Zhmoginov, L.-C. Chen, "MobileNetV2: Inverted Residuals and Linear Bottlenecks", CVPR 2018, pp. 4510-4520 | arXiv 1801.04381; DOI 10.1109/CVPR.2018.00474 | SSDLite, the lighter successor to the current SSD + MobileNet setup | Downloaded |
| tan2020_efficientdet.pdf | M. Tan, R. Pang, Q. V. Le, "EfficientDet: Scalable and Efficient Object Detection", CVPR 2020, pp. 10778-10787 | arXiv 1911.09070; DOI 10.1109/CVPR42600.2020.01079 | Background for the EfficientDet-Lite models, a candidate upgrade | Downloaded |
| redmon2016_yolo.pdf | J. Redmon, S. Divvala, R. Girshick, A. Farhadi, "You Only Look Once: Unified, Real-Time Object Detection", CVPR 2016, pp. 779-788 | arXiv 1506.02640; DOI 10.1109/CVPR.2016.91 | Where the YOLO family (including YOLOv8) comes from | Downloaded |
| terven2023_yolo_review.pdf | J. Terven, D.-M. Cordova-Esparza, J.-A. Romero-Gonzalez, "A Comprehensive Review of YOLO Architectures in Computer Vision: From YOLOv1 to YOLOv8 and YOLO-NAS", Machine Learning and Knowledge Extraction, vol. 5, no. 4, pp. 1680-1716, 2023 | arXiv 2304.00501; DOI 10.3390/make5040083 | Citable description of YOLOv8, which has no paper of its own | Downloaded |
| yosinski2014_transferable.pdf | J. Yosinski, J. Clune, Y. Bengio, H. Lipson, "How transferable are features in deep neural networks?", Advances in Neural Information Processing Systems 27 (NIPS 2014), pp. 3320-3328 | arXiv 1411.1792 | Why fine-tuning a pretrained model on a small campus dataset works | Downloaded |
| cordts2016_cityscapes.pdf | M. Cordts, M. Omran, S. Ramos, T. Rehfeld, M. Enzweiler, R. Benenson, U. Franke, S. Roth, B. Schiele, "The Cityscapes Dataset for Semantic Urban Scene Understanding", CVPR 2016, pp. 3213-3223 | arXiv 1604.01685; DOI 10.1109/CVPR.2016.350 | Colour-coded pixel labels (semantic segmentation) for urban driving scenes | Downloaded |
| zhu2019_monocular_distance.pdf | J. Zhu, Y. Fang, "Learning Object-Specific Distance From a Monocular Image", ICCV 2019, pp. 3838-3847 | arXiv 1909.04182; DOI 10.1109/ICCV.2019.00394 | Estimating distance to a detected object from one camera; a comparison point for the pinhole-distance heuristic | Downloaded |
| arya2022_rdd2022.pdf | D. Arya, H. Maeda, S. K. Ghosh, D. Toshniwal, Y. Sekimoto, "RDD2022: A multi-national image dataset for automatic Road Damage Detection", arXiv preprint, 2022 | arXiv 2209.08538 | A ready dataset if potholes and cracks are added as hazards | Downloaded |
| dhall2019_traffic_cones.pdf | A. Dhall, D. Dai, L. Van Gool, "Real-time 3D Traffic Cone Detection for Autonomous Driving", IEEE Intelligent Vehicles Symposium (IV) 2019, pp. 494-501 | arXiv 1902.02394; DOI 10.1109/IVS.2019.8814089 | Detecting traffic cones, a likely campus object that COCO does not include | Downloaded |
| alqahtani2024_edge_benchmark.pdf | D. K. Alqahtani, M. A. Cheema, M. A. Rodriguez, A. N. Toosi, "A Comprehensive Evaluation of Deep Learning Object Detection Models on Heterogeneous Edge Devices", arXiv preprint (v1 2024, v3 July 2026) | arXiv 2409.16808 | Measured speed, energy and accuracy of SSD MobileNet, EfficientDet-Lite and YOLOv8 on a Raspberry Pi 4 (CPU only and with Coral TPU) | Downloaded (v3) |
| bruce2000_cmvision.pdf | J. Bruce, T. Balch, M. Veloso, "Fast and Inexpensive Color Image Segmentation for Interactive Robots", Proc. IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS 2000), vol. 3, pp. 2061-2066, 2000 | DOI 10.1109/IROS.2000.895274 | Classical colour thresholding (no learning), and why the choice of colour space matters when lighting changes | Downloaded (open copy from Carnegie Mellon Robotics Institute) |
| chan2021_segmentmeifyoucan.pdf | See file | See file | Already in the library | Already in references_pdf |
| choe2023_hazardnet.pdf | See file | See file | Already in the library | Already in references_pdf |
| liu2023_grounding_dino.pdf | See file | See file | Already in the library | Already in references_pdf |
| tanveer2026_yolov8n_roadside.pdf | See file | See file | Already in the library | Already in references_pdf |

The four "already in references_pdf" files sit one folder up (references_pdf\). They were not re-verified in this pass, so their citations are not repeated here.

### Notes on author lists

- COCO: the arXiv version lists 10 authors (it also includes Lubomir Bourdev and Ross Girshick). The published ECCV 2014 version lists 8. The table and .bib use the published list.
- Zhu 2019: the arXiv version lists 6 authors (Jing Zhu, Yi Fang, Husam Abu-Haimed, Kuo-Chin Lien, Dongdong Fu, Junli Gu). The published ICCV 2019 version lists only Jing Zhu and Yi Fang. The table and .bib use the published list.
- Terven 2023: the arXiv version lists 2 authors (Juan Terven, Diana Cordova-Esparza). The published MDPI version adds Julio-Alejandro Romero-Gonzalez. The table and .bib use the published list and title.
- Alqahtani: the paper reports inference time in milliseconds, not fps. You get fps as 1000 divided by the time in ms, for example 209 ms per frame is about 4.8 fps. This paper is an arXiv preprint; no peer-reviewed version was found in this check.

## Plain-language summaries (from the abstracts only)

liu2016_ssd (SSD). SSD finds objects in an image with a single neural network, by placing a fixed set of "default boxes" of different shapes and sizes across the image and, for each one, scoring which object class is present and nudging the box to fit. It combines predictions from several feature maps of different resolutions so it can handle both small and large objects, and it skips the separate "propose regions first" step used by older detectors. The authors report accuracy comparable to those slower two-stage methods while being much faster, for example 72.1% mAP at 58 FPS on a desktop GPU for 300 by 300 input.

howard2017_mobilenets (MobileNets). MobileNets are a family of small, efficient networks for phones and embedded devices, built from depthwise separable convolutions, which do much less arithmetic than normal convolutions. Two simple settings let you shrink or grow the model to trade speed against accuracy. The authors show good results on ImageNet classification and on other tasks including object detection.

lin2014_coco (COCO). COCO is a large image dataset of complex everyday scenes where common objects appear in their natural context, not posed or centred. It covers 91 object types with 2.5 million labelled instances in 328 thousand images, and each object is outlined precisely (per-instance segmentation), collected with the help of crowd workers. The paper compares its statistics with PASCAL, ImageNet and SUN and gives baseline detection results.

jacob2018_quantization (8-bit quantization). The paper proposes a way to run a neural network using only integer arithmetic, which is faster than floating point on typical mobile hardware. It also gives a training procedure that keeps accuracy high after the model is converted to integers. The gains hold even for MobileNets, and are shown on ImageNet classification and COCO detection running on ordinary CPUs.

sandler2018_mobilenetv2 (MobileNetV2 and SSDLite). MobileNetV2 is an improved mobile network built from "inverted residual" blocks with thin bottleneck layers and lightweight depthwise convolutions, and the authors found it important to remove non-linearities in the narrow layers. The paper also introduces SSDLite, an efficient way to use these mobile networks for object detection, and Mobile DeepLabv3 for segmentation. Results are reported on ImageNet, COCO detection and VOC segmentation, measured against compute (multiply-adds) and parameter count.

tan2020_efficientdet (EfficientDet). The authors study how to design object detectors efficiently and propose two ideas: BiFPN, a fast way of mixing features at several scales, and compound scaling, which grows image resolution, network depth and width together in a balanced way. The result is the EfficientDet family, which gets better accuracy for a given compute budget than earlier detectors across a wide range of sizes. Their largest model reaches 55.1 AP on COCO while being 4 to 9 times smaller than previous detectors.

redmon2016_yolo (YOLO). YOLO treats detection as one regression problem: a single network looks at the whole image once and directly predicts bounding boxes and class probabilities. Because it is one network it can be trained end to end and is very fast, 45 frames per second for the base model and 155 for the smaller Fast YOLO. It makes more localisation errors than the best systems of the time but fewer false detections on background, and it generalises well from photos to artwork.

terven2023_yolo_review (YOLO review). This review traces how YOLO evolved from the original version up to YOLOv8, YOLO-NAS and transformer-based YOLO variants. It first explains the standard evaluation metrics and post-processing, then describes the main architecture and training changes in each version. It closes with lessons learned and future research directions for real-time detection.

yosinski2014_transferable (transfer learning). Networks trained on natural images learn very general features in their first layers (edge-like filters and colour blobs) and more task-specific features in later layers. The authors measure how general or specific each layer is and find that transfer gets harder as the new task differs more from the original, yet transferred features still beat random starting weights. They also find that starting from transferred features improves generalisation even after fine-tuning on the new dataset.

cordts2016_cityscapes (Cityscapes). Cityscapes is a benchmark and large dataset for pixel-level and instance-level labelling of urban street scenes, recorded as stereo video in 50 cities. It has 5000 images with high-quality pixel labels and 20000 more with coarse labels. The paper analyses the dataset and evaluates several state-of-the-art methods on it.

zhu2019_monocular_distance (distance from one camera). The traditional approach of inverse perspective mapping (assuming a flat road and projecting from the image) works poorly for far-away objects and on curved roads. The authors train an end-to-end model that directly predicts the distance to each detected object, plus an enhanced version with a keypoint regressor that helps especially for close objects. They extend the KITTI and nuScenes datasets with per-object distances and show their methods beat inverse perspective mapping and an SVR baseline.

arya2022_rdd2022 (road damage dataset). RDD2022 contains 47,420 road images from Japan, India, the Czech Republic, Norway, the United States and China, with more than 55,000 labelled instances of road damage. It covers four types: longitudinal cracks, transverse cracks, alligator cracks and potholes. It was released for the CRDDC2022 challenge and is meant for training and benchmarking automatic road damage detectors.

dhall2019_traffic_cones (traffic cones). Most road-scene perception work focuses on cars and pedestrians, so this paper targets traffic cones. It detects cones with a tailored 2D detector, finds keypoints on each cone with a regression network, then recovers each cone's 3D position with the classical Perspective-n-Point algorithm. It runs in real time on a low-power Jetson TX2 and was used on a Formula Student race car that drove autonomously on tracks marked by cones.

alqahtani2024_edge_benchmark (edge device benchmark). The authors benchmark YOLOv8 (Nano, Small, Medium), EfficientDet Lite (Lite0 to Lite2) and SSD (SSD MobileNet V1, SSDLite MobileDet) on Raspberry Pi 3, 4 and 5 with and without a Coral TPU, a Pi 5 with AI HAT+, a Jetson Nano and a Jetson Orin Nano, measuring energy, inference time and accuracy. SSD MobileNet V1 had the lowest latency and energy use but the lowest accuracy, while YOLOv8 Medium was most accurate but most expensive. The accuracy gap between models widens as scenes contain more objects.

bruce2000_cmvision (colour thresholding, abstract read from the PDF, since this paper is not on arXiv). The paper describes a software system that segments camera images by colour in real time on ordinary PC hardware, tracking several hundred regions of up to 32 colours at 30 Hz, used in robot soccer (RoboCup) and similar settings. Each pixel is classified by checking whether its colour values fall inside threshold ranges, then neighbouring same-colour pixels are merged into regions, with a trick that makes the threshold check cost only two logical AND operations. The body of the paper (section 2.1) explains why a colour space that separates brightness from colour, such as YUV or HSI, is used: robustness to changes in the brightness of illumination, which plain RGB thresholds handle poorly.

## Glossary

Object detection: finding where objects are in an image and what they are. The output is a list of boxes, each with a class label and a confidence score.

Bounding box: the rectangle drawn around a detected object, usually given as its corner coordinates in pixels.

Backbone: the first part of a detector, a network (for example MobileNet) that turns the raw image into a set of features. The detection "head" (for example SSD) then uses those features to predict boxes.

Pretrained: a model whose weights were already learned on a large dataset by someone else, so you can use it straight away without training it yourself.

COCO: Common Objects in Context, the large labelled image dataset most off-the-shelf detectors are trained on. A COCO-trained model can only name the object classes COCO contains.

mAP: mean Average Precision, the standard accuracy score for detectors. It combines how many real objects were found and how many detections were correct, averaged over all classes. Higher is better.

Quantization: storing a model's numbers as 8-bit integers instead of 32-bit floating point. The model gets about four times smaller and runs faster on CPUs, usually with a small loss of accuracy.

Fine-tuning / transfer learning: taking a pretrained model and training it a little more on your own, smaller dataset (for example campus photos with cones), so it learns new classes or conditions while keeping what it already knew.

Semantic segmentation: labelling every pixel in an image with a class (road, pavement, person, car). Datasets like Cityscapes show this as a colour-coded image where each colour means one class.

Colour thresholding: a classical method with no learning, where a pixel is marked as "object" if its colour values fall inside chosen ranges (for example a range of hue for orange). It is fast but sensitive to lighting, shadows and other objects of the same colour.

Inference: running a trained model on new input to get predictions, as opposed to training it.

fps: frames per second, how many camera frames the system can process each second. It equals 1000 divided by the processing time per frame in milliseconds.
