import sys
from pathlib import Path

import cv2
import torch
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit
)


class LPOCRApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.current_image_path = None
        self.init_ui()
        self.load_model()

    def init_ui(self):
        self.setGeometry(100, 100, 900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("OCR TEST")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            padding: 15px;
            background-color: #ecf0f1;
            border-radius: 8px;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(title_label)

        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)

        self.image_label = QLabel("Chưa có ảnh được chọn")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(600, 400)
        self.image_label.setStyleSheet("""
            border: 2px dashed #bdc3c7;
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            font-size: 16px;
            color: #7f8c8d;
        """)
        image_layout.addWidget(self.image_label)
        main_layout.addWidget(image_container)

        button_layout = QHBoxLayout()

        self.upload_btn = QPushButton("📁 Upload Ảnh")
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                min-width: 150px;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #21618c; }
        """)
        self.upload_btn.clicked.connect(self.upload_image)

        self.detect_btn = QPushButton("🔍 Nhận Diện")
        self.detect_btn.setEnabled(False)
        self.detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                min-width: 150px;
            }
            QPushButton:hover { background-color: #27ae60; }
            QPushButton:pressed { background-color: #1e8449; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.detect_btn.clicked.connect(self.detect_ocr)

        self.clear_btn = QPushButton("🗑️ Xóa")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                min-width: 150px;
            }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:pressed { background-color: #a93226; }
        """)
        self.clear_btn.clicked.connect(self.clear_all)

        button_layout.addStretch()
        button_layout.addWidget(self.upload_btn)
        button_layout.addWidget(self.detect_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        result_container = QWidget()
        result_layout = QVBoxLayout(result_container)

        result_title = QLabel("📊 Kết quả OCR:")
        result_title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 15px;
        """)
        result_layout.addWidget(result_title)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(140)
        self.result_text.setStyleSheet("""
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            padding: 10px;
            font-size: 16px;
            background-color: #ffffff;
        """)
        result_layout.addWidget(self.result_text)
        main_layout.addWidget(result_container)

        self.status_label = QLabel("Đã sẵn sàng")
        self.status_label.setStyleSheet("""
            padding: 8px;
            background-color: #ecf0f1;
            border-radius: 4px;
            font-size: 14px;
            color: #34495e;
        """)
        main_layout.addWidget(self.status_label)

    def load_model(self):
        try:
            base_dir = Path(__file__).resolve().parent

            # Ưu tiên nano, fallback sang file thường nếu có
            candidates = [
                base_dir / "LP_ocr_nano.pt",
            ]
            model_path = next((p for p in candidates if p.exists()), None)

            if model_path is None:
                self._set_status_error("❌ Lỗi: Không tìm thấy model (LP_ocr_nano.pt)")
                return

            self.model = torch.hub.load(
                "ultralytics/yolov5",
                "custom",
                path=str(model_path),
                force_reload=False
            )
            self.model.to(self.device)

            # Giảm conf để hạn chế “mất ký tự” (ví dụ số 1)
            self.model.conf = 0.10
            # Giảm NMS quá gắt (tuỳ bài)
            self.model.iou = 0.45

            self._set_status_ok(f"✅ Model đã load: {model_path.name} ({self.device})")
        except Exception as e:
            self._set_status_error(f"❌ Lỗi khi load model: {e}")

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh ", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if not file_path:
            return

        self.current_image_path = file_path

        pixmap = QPixmap(file_path)
        scaled_pixmap = pixmap.scaled(
            self.image_label.width() - 40,
            self.image_label.height() - 40,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setStyleSheet("""
            border: 2px solid #3498db;
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
        """)

        self.detect_btn.setEnabled(True)
        self._set_status_info(f"✅ Đã load ảnh: {Path(file_path).name}")

    def detect_ocr(self):
        if not self.current_image_path or self.model is None:
            return

        try:
            self._set_status_processing("🔄 Đang xử lý...")
            QApplication.processEvents()

            img = cv2.imread(self.current_image_path)
            if img is None:
                self._set_status_error("❌ Không đọc được ảnh.")
                return

            results = self.model(img)
            det = results.pandas().xyxy[0]

            if det is None or len(det) == 0:
                self.result_text.setPlainText("❌ Không phát hiện được ký tự nào trên ảnh.")
                self._set_status_warn("⚠️ Không phát hiện số nào.")
                return

            det = det.copy()
            det["xc"] = (det["xmin"] + det["xmax"]) / 2
            det["yc"] = (det["ymin"] + det["ymax"]) / 2

            # Heuristic: nếu 2 dòng, sort theo dòng (y), rồi theo x
            # Ngưỡng tách dòng = 0.35 * chiều cao trung bình bbox
            h_med = (det["ymax"] - det["ymin"]).median()
            y_thresh = float(h_med * 0.35) if h_med > 0 else 10.0

            det = det.sort_values(["yc", "xc"])
            # Gán row_id theo cụm y gần nhau
            row_ids = []
            current_row = 0
            last_y = None
            for y in det["yc"].tolist():
                if last_y is None:
                    row_ids.append(current_row)
                    last_y = y
                    continue
                if abs(y - last_y) > y_thresh:
                    current_row += 1
                row_ids.append(current_row)
                last_y = y
            det["row_id"] = row_ids

            # Sort cuối: row_id rồi xc
            det = det.sort_values(["row_id", "xc"])

            # Lọc các ký tự có độ tin cậy thấp (< 50%)
            confidence_threshold = 0.5
            det_filtered = det[det["confidence"] >= confidence_threshold].copy()
            
            license_plate = ""
            lines = [f"Tìm thấy {len(det_filtered)}):\n"]
            for _, d in det_filtered.iterrows():
                char = str(d["name"])
                conf = float(d["confidence"])
                license_plate += char
                lines.append(f"  {char} (Độ tin cậy: {conf:.2%})")

            lines.append("\n═══════════════════════")
            lines.append(f"SỐ: {license_plate}")
            lines.append("═══════════════════════")

            self.result_text.setPlainText("\n".join(lines))
            self._set_status_ok(f"✅ Nhận diện thành công: {license_plate}")

            self.draw_results(img, det_filtered, license_plate)

        except Exception as e:
            self.result_text.setPlainText(f"❌ Lỗi: {e}")
            self._set_status_error("❌ Lỗi khi nhận diện")

    def draw_results(self, img, det, license_plate):
        img_copy = img.copy()

        for _, d in det.iterrows():
            x1, y1, x2, y2 = map(int, [d["xmin"], d["ymin"], d["xmax"], d["ymax"]])
            conf = float(d["confidence"])
            char = str(d["name"])

            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)

            label = f"{char} {conf:.2f}"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            y_top = max(0, y1 - lh - 10)
            cv2.rectangle(img_copy, (x1, y_top), (x1 + lw, y1), (0, 255, 0), -1)
            cv2.putText(img_copy, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        text = f"Số: {license_plate}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        cv2.rectangle(img_copy, (10, 10), (10 + tw + 20, 10 + th + 20), (0, 255, 0), -1)
        cv2.putText(img_copy, text, (20, 10 + th + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)

        h, w, _ = img_copy.shape
        q_img = QImage(img_copy.data, w, h, 3 * w, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(q_img)

        scaled_pixmap = pixmap.scaled(
            self.image_label.width() - 40,
            self.image_label.height() - 40,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def clear_all(self):
        self.current_image_path = None
        self.image_label.clear()
        self.image_label.setText("Chưa có ảnh được chọn")
        self.image_label.setStyleSheet("""
            border: 2px dashed #bdc3c7;
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            font-size: 16px;
            color: #7f8c8d;
        """)
        self.result_text.clear()
        self.detect_btn.setEnabled(False)
        self.status_label.setText("Đã xóa tất cả")
        self.status_label.setStyleSheet("""
            padding: 8px;
            background-color: #ecf0f1;
            border-radius: 4px;
            font-size: 14px;
            color: #34495e;
        """)

    # ===== Helpers set status =====
    def _set_status_ok(self, msg):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("""
            padding: 8px; background-color: #2ecc71; border-radius: 4px;
            font-size: 14px; color: white; font-weight: bold;
        """)

    def _set_status_error(self, msg):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("""
            padding: 8px; background-color: #e74c3c; border-radius: 4px;
            font-size: 14px; color: white; font-weight: bold;
        """)

    def _set_status_warn(self, msg):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("""
            padding: 8px; background-color: #e67e22; border-radius: 4px;
            font-size: 14px; color: white; font-weight: bold;
        """)

    def _set_status_info(self, msg):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("""
            padding: 8px; background-color: #3498db; border-radius: 4px;
            font-size: 14px; color: white;
        """)

    def _set_status_processing(self, msg):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("""
            padding: 8px; background-color: #f39c12; border-radius: 4px;
            font-size: 14px; color: white; font-weight: bold;
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = LPOCRApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
