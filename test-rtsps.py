import cv2

cap = cv2.VideoCapture("rtsps://cr-14.hostedcloudvideo.com:443/publish-cr/_definst_/G0W2EP7IKAXYETM1ANDVQ6DBRXNXCN7VK3MM7SP9/6b55ae911a8dbd2bd7d3a75ae4547acc976d0b9e?action=PLAY")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("RTSP Stream", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
