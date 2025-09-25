#!/usr/bin/env python3
"""
Headless Bison Tracking Script for Server/Cluster Environment
No GUI display - perfect for remote servers and clusters.
"""

import os
import time
import cv2
import numpy as np
from ultralytics import YOLO

# ─── PARAMETERS ────────────────────────────────────────────────────────────────
# VIDEO_SOURCE   = "DJI_bison.MP4"
VIDEO_SOURCE   = "rtsps://cr-14.hostedcloudvideo.com:443/publish-cr/_definst_/G0W2EP7IKAXYETM1ANDVQ6DBRXNXCN7VK3MM7SP9/6b55ae911a8dbd2bd7d3a75ae4547acc976d0b9e?action=PLAY"  # Path to your video file
OUTPUT_PATH    = "Bison-tracked_new.mp4"
TRACKER_CFG    = "args.yaml"
# MODEL_WEIGHTS  = "/mmfs1/home/andrews.danyo/Bison Guard/Bison/Bison_annotated/large_model_yolo11x_automatic_batch_size/train4/weights/best.pt"
MODEL_WEIGHTS = "best.pt"
CLASS_NAMES    = ["bison"]
MIN_CONFIDENCE = 0.3
HEADLESS_MODE  = True
PROGRESS_INTERVAL = 100
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Headless Bison Tracking with ByteTracker")
    print("=" * 60)
    
    # 1. Load model and verify tracker config
    print(f"Loading model: {MODEL_WEIGHTS}")
    model = YOLO(MODEL_WEIGHTS)
    
    if not os.path.isfile(TRACKER_CFG):
        raise FileNotFoundError(f"Tracker config not found: {TRACKER_CFG}")
    print(f"Using tracker config: {TRACKER_CFG}")

    # 2. Open video source
    print(f"Opening video: {VIDEO_SOURCE}")
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {VIDEO_SOURCE}")

    # Get video properties
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video properties:")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Total frames: {total_frames}")
    print(f"  Duration: {total_frames/fps:.1f} seconds")

    # 3. Prepare VideoWriter to save output
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))
    print(f"Output will be saved to: {OUTPUT_PATH}")

    # 4. Processing loop
    print(f"\nStarting processing...")
    print(f"Progress updates every {PROGRESS_INTERVAL} frames")
    print("-" * 60)
    
    frame_count = 0
    start_time = time.time()
    total_bison_detections = 0
    max_bison_in_frame = 0
    
    try:
        while True:
            loop_start = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # Rotate 180° because video is upside down
            #frame = cv2.rotate(frame, cv2.ROTATE_180)

            # Detect + track via ByteTrack
            results = model.track(
                source=frame,
                tracker=TRACKER_CFG,
                conf=MIN_CONFIDENCE,
                persist=True,
                verbose=False  # Suppress YOLO output for cleaner logs
            )[0]

            # Extract and convert for iteration
            boxes = results.boxes
            bison_count = 0
            
            if boxes is not None:
                coords     = boxes.xyxy.tolist()
                cls_list   = boxes.cls.tolist()
                ids_tensor = boxes.id
                id_list    = ids_tensor.tolist() if ids_tensor is not None else [None]*len(cls_list)
                conf_list  = boxes.conf.tolist()

                # Count & draw
                for (x1, y1, x2, y2), tid, cls, conf in zip(coords, id_list, cls_list, conf_list):
                    cls = int(cls)
                    if cls >= len(CLASS_NAMES) or CLASS_NAMES[cls] != "bison":
                        continue

                    bison_count += 1
                    x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
                    
                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw ID and confidence
                    if tid is not None:
                        label = f"ID {int(tid)} ({conf:.2f})"
                    else:
                        label = f"Bison ({conf:.2f})"
                        
                    cv2.putText(frame, label,
                               (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
            # Update statistics
            total_bison_detections += bison_count
            max_bison_in_frame = max(max_bison_in_frame, bison_count)

            # Overlay count and FPS on frame
            fps_display = 1.0 / (time.time() - loop_start + 1e-6)
            cv2.putText(frame, f"Count: {bison_count}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            cv2.putText(frame, f"FPS: {fps_display:.1f}",
                       (width - 140, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            cv2.putText(frame, f"Frame: {frame_count}/{total_frames}",
                       (10, height - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Write frame to output file
            cv2.imshow("Bison Tracking", frame) 
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            writer.write(frame)

            # Progress updates (no GUI display in headless mode)
            if frame_count % PROGRESS_INTERVAL == 0 or frame_count == 1:
                elapsed = time.time() - start_time
                progress = (frame_count / total_frames) * 100
                eta = (elapsed / frame_count) * (total_frames - frame_count)
                avg_fps = frame_count / elapsed
                
                print(f"Frame {frame_count:5d}/{total_frames} ({progress:5.1f}%) | "
                      f"Bison: {bison_count:2d} | "
                      f"FPS: {avg_fps:5.1f} | "
                      f"ETA: {eta/60:4.1f}m")

    except KeyboardInterrupt:
        print(f"\nProcessing interrupted by user at frame {frame_count}")
    except Exception as e:
        print(f"\nError during processing: {e}")
    finally:
        # Cleanup
        cap.release()
        writer.release()
        # No cv2.destroyAllWindows() needed in headless mode

    # Final statistics
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETED")
    print("=" * 60)
    print(f"Total frames processed: {frame_count:,}")
    print(f"Total processing time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"Average processing FPS: {frame_count/total_time:.1f}")
    print(f"Max bison in single frame: {max_bison_in_frame}")
    print(f"Average bison per frame: {total_bison_detections/frame_count:.1f}")
    print(f"Output saved to: {OUTPUT_PATH}")
    
    # File size info
    if os.path.exists(OUTPUT_PATH):
        file_size = os.path.getsize(OUTPUT_PATH) / (1024*1024)  # MB
        print(f"Output file size: {file_size:.1f} MB")
    
    print("=" * 60)

if __name__ == "__main__":
    main()



# import os
# import time
# import cv2
# import numpy as np
# from ultralytics import YOLO

# # # ─── PARAMETERS ────────────────────────────────────────────────────────────────
# # VIDEO_SOURCE   = "Bison Guard/Bison/Bison_annotated/DJI_bison.MP4"   # or 0 for webcam
# # OUTPUT_PATH    = "Bison Guard/Bison/Bison_annotated/Bison-tracked_output.mp4"
# # TRACKER_CFG = "Bison Guard/Bison/Bison_annotated/args.yaml"
# # #TRACKER_CFG    = "Bison Guard/Bison/Bison_annotated/args.yaml/args.yaml"        # your ByteTrack YAML
# # #MODEL_WEIGHTS  = "Bison Guard/Bison/Bison_annotated/large_model_yolo11x_automatic_batch_size/train4/weights/best.pt"
# # MODEL_WEIGHTS = "large_model_yolo11x_automatic_batch_size/train4/weights/best.pt"
# # CLASS_NAMES    = ["bison"]                                # model’s class order
# # MIN_CONFIDENCE = 0.3
# # # ──────────────────────────────────────────────────────────────────────────────

# # ─── CORRECTED PARAMETERS ─────────────────────────────────────────────────
# VIDEO_SOURCE   = "DJI_bison.MP4"
# OUTPUT_PATH    = "Bison Guard/Bison/Bison_annotated/Bison-tracked_output.mp4"
# TRACKER_CFG    = "args.yaml"  # ← Fixed this
# MODEL_WEIGHTS  = "large_model_yolo11x_automatic_batch_size/train4/weights/best.pt"
# CLASS_NAMES    = ["bison"]
# MIN_CONFIDENCE = 0.3

# def main():
#     # 1. Load model and verify tracker config
#     model = YOLO(MODEL_WEIGHTS)
#     if not os.path.isfile(TRACKER_CFG):
#         raise FileNotFoundError(f"Tracker config not found: {TRACKER_CFG}")

#     # 2. Open video source
#     cap = cv2.VideoCapture(VIDEO_SOURCE)
#     if not cap.isOpened():
#         raise RuntimeError(f"Cannot open source: {VIDEO_SOURCE}")

#     width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0

#     # 3. Prepare VideoWriter to save output
#     fourcc = cv2.VideoWriter_fourcc(*"mp4v")
#     writer = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

#     # 4. Processing loop
#     while True:
#         start_time = time.time()
#         ret, frame = cap.read()
#         if not ret:
#             break

#         # rotate 180° because video is upside down
#         frame = cv2.rotate(frame, cv2.ROTATE_180)

#         # detect + track via ByteTrack
#         results = model.track(
#             source=frame,
#             tracker=TRACKER_CFG,
#             conf=MIN_CONFIDENCE,
#             persist=True
#         )[0]

#         # extract and convert for iteration
#         boxes      = results.boxes
#         coords     = boxes.xyxy.tolist()
#         cls_list   = boxes.cls.tolist()
#         ids_tensor = boxes.id
#         id_list    = ids_tensor.tolist() if ids_tensor is not None else [None]*len(cls_list)

#         # count & draw
#         bison_count = 0
#         for (x1, y1, x2, y2), tid, cls in zip(coords, id_list, cls_list):
#             cls = int(cls)
#             if CLASS_NAMES[cls] != "bison":
#                 continue

#             bison_count += 1
#             x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
#             cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#             if tid is not None:
#                 cv2.putText(frame, f"ID {int(tid)}",
#                             (x1, y1 - 10),
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

#         # overlay count and FPS
#         fps_display = 1.0 / (time.time() - start_time + 1e-6)
#         cv2.putText(frame, f"Count: {bison_count}",
#                     (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
#         cv2.putText(frame, f"FPS: {fps_display:.1f}",
#                     (width - 140, 30),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

#         # write frame to output file
#         writer.write(frame)

#         # display in real time; quit on 'q'
#         cv2.imshow("Real-Time Bison Tracking", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     # cleanup
#     cap.release()
#     writer.release()
#     cv2.destroyAllWindows()
#     print(f"→ Done. Processed video saved to: {OUTPUT_PATH}")

# if __name__ == "__main__":
#     main()
