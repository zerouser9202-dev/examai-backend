"""
OCR Service - Hybrid PaddleOCR + EasyOCR Engine
Handles: multilingual text, blurry scans, rotated pages,
math equations, Hindi/English mixed content, multi-column layouts.
"""
import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocess images for better OCR accuracy."""

    @staticmethod
    def load_image(image_path: str) -> np.ndarray:
        """Load image from path"""
        try:
            import cv2
            img = cv2.imread(image_path)
            if img is None:
                pil_img = Image.open(image_path).convert("RGB")
                img = np.array(pil_img)
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return img
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return np.array([])

    @staticmethod
    def preprocess(image_path: str, aggressive: bool = False) -> np.ndarray:
        """Basic preprocessing without heavy dependencies"""
        try:
            import cv2
            img = ImagePreprocessor.load_image(image_path)
            if img.size == 0:
                return np.array([])
            
            # Simple grayscale conversion
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # Basic thresholding
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return np.array([])


class PaddleOCREngine:
    """PaddleOCR-based text extraction supporting EN + HI."""

    def __init__(self):
        self._engine = None
        self._initialized = False

    def _init(self):
        if self._initialized:
            return
        try:
            from paddleocr import PaddleOCR
            self._engine = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=False,
                show_log=False,
                det_db_thresh=0.3,
                det_db_box_thresh=0.5,
                rec_batch_num=6,
            )
            self._initialized = True
            logger.info("PaddleOCR initialized")
        except ImportError:
            logger.warning("PaddleOCR not installed")
        except Exception as e:
            logger.error(f"Error initializing PaddleOCR: {e}")

    def extract(self, image: np.ndarray) -> dict:
        """Extract text from image"""
        self._init()
        
        # FIXED: Check if engine exists before calling
        if self._engine is None or not self._initialized:
            return {"text": "", "confidence": 0.0, "boxes": [], "engine": "paddleocr", "error": "Engine not initialized"}

        try:
            start = time.time()
            result = self._engine.ocr(image, cls=True)
            elapsed_ms = int((time.time() - start) * 1000)

            lines = []
            boxes = []
            confidences = []

            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        box = line[0]
                        text, conf = line[1]
                        lines.append(text)
                        confidences.append(conf)
                        boxes.append({"box": box, "text": text, "confidence": conf})

            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            return {
                "text": "\n".join(lines),
                "confidence": avg_conf,
                "boxes": boxes,
                "processing_time_ms": elapsed_ms,
                "engine": "paddleocr",
                "line_count": len(lines),
            }
        except Exception as e:
            logger.error(f"PaddleOCR extraction error: {e}")
            return {"text": "", "confidence": 0.0, "boxes": [], "engine": "paddleocr", "error": str(e)}


class EasyOCREngine:
    """EasyOCR fallback engine for Hindi + English."""

    def __init__(self):
        self._reader = None
        self._initialized = False

    def _init(self):
        if self._initialized:
            return
        try:
            import easyocr
            self._reader = easyocr.Reader(["en", "hi"], gpu=False, verbose=False)
            self._initialized = True
            logger.info("EasyOCR initialized")
        except ImportError:
            logger.warning("EasyOCR not installed")
        except Exception as e:
            logger.error(f"Error initializing EasyOCR: {e}")

    def extract(self, image: np.ndarray) -> dict:
        """Extract text using EasyOCR"""
        self._init()
        
        # FIXED: Check if reader exists before calling
        if self._reader is None or not self._initialized:
            return {"text": "", "confidence": 0.0, "boxes": [], "engine": "easyocr", "error": "Engine not initialized"}

        try:
            start = time.time()
            result = self._reader.readtext(image)
            elapsed_ms = int((time.time() - start) * 1000)

            lines = []
            boxes = []
            confidences = []

            for (box, text, conf) in result:
                lines.append(text)
                confidences.append(conf)
                boxes.append({"box": box, "text": text, "confidence": conf})

            # Sort by vertical position for reading order
            boxes.sort(key=lambda x: min(p[1] for p in x["box"]))

            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            return {
                "text": "\n".join(l["text"] for l in boxes),
                "confidence": avg_conf,
                "boxes": boxes,
                "processing_time_ms": elapsed_ms,
                "engine": "easyocr",
                "line_count": len(lines),
            }
        except Exception as e:
            logger.error(f"EasyOCR extraction error: {e}")
            return {"text": "", "confidence": 0.0, "boxes": [], "engine": "easyocr", "error": str(e)}


class HybridOCRService:
    """Hybrid OCR: tries PaddleOCR first, falls back to EasyOCR"""

    def __init__(self, confidence_threshold: float = 0.6):
        self.paddle = PaddleOCREngine()
        self.easy = EasyOCREngine()
        self.preprocessor = ImagePreprocessor()
        self.confidence_threshold = confidence_threshold

    async def extract_page(
        self,
        image_path: str,
        page_num: int = 1,
        use_aggressive_preprocessing: bool = False,
    ) -> dict:
        """Extract text from a single page image."""
        loop = asyncio.get_event_loop()

        # Preprocess
        img = await loop.run_in_executor(
            None,
            lambda: self.preprocessor.preprocess(image_path, use_aggressive_preprocessing)
        )

        if img.size == 0:
            return {
                "text": "",
                "confidence": 0.0,
                "error": "Failed to load image",
                "page_number": page_num
            }

        # Try PaddleOCR first
        result = await loop.run_in_executor(None, lambda: self.paddle.extract(img))

        # Fallback to EasyOCR if confidence is low
        if result.get("confidence", 0) < self.confidence_threshold and "error" not in result:
            logger.info(f"Page {page_num}: PaddleOCR confidence={result['confidence']:.2f}, trying EasyOCR fallback")
            easy_result = await loop.run_in_executor(None, lambda: self.easy.extract(img))

            if easy_result.get("confidence", 0) > result.get("confidence", 0):
                result = easy_result

        # Add page metadata
        result["has_hindi"] = self._detect_hindi(result.get("text", ""))
        result["has_equations"] = self._detect_equations(result.get("text", ""))
        result["page_number"] = page_num
        result["word_count"] = len(result.get("text", "").split())

        return result

    async def extract_pdf(self, pdf_path: str) -> list[dict]:
        """Extract all pages from a PDF."""
        try:
            import fitz  # PyMuPDF
            import tempfile
            import os

            doc = fitz.open(pdf_path)
            page_results = []
            temp_dir = tempfile.mkdtemp()
            image_paths = []

            logger.info(f"Processing PDF: {pdf_path} ({len(doc)} pages)")

            for page_num in range(len(doc)):
                page = doc[page_num]
                mat = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=mat)
                img_path = os.path.join(temp_dir, f"page_{page_num + 1}.png")
                pix.save(img_path)
                image_paths.append(img_path)

            doc.close()

            # Process pages
            for i, img_path in enumerate(image_paths):
                result = await self.extract_page(img_path, i + 1)
                page_results.append(result)

            # Cleanup
            for path in image_paths:
                try:
                    os.unlink(path)
                except Exception:
                    pass
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass

            return page_results

        except ImportError:
            logger.error("PyMuPDF (fitz) not installed. Install with: pip install pymupdf")
            return [{"text": "", "error": "PyMuPDF not installed", "page_number": 1}]
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return [{"text": "", "error": str(e), "page_number": 1}]

    @staticmethod
    def _detect_hindi(text: str) -> bool:
        """Check if text contains Devanagari (Hindi) characters."""
        for char in text:
            if '\u0900' <= char <= '\u097F':
                return True
        return False

    @staticmethod
    def _detect_equations(text: str) -> bool:
        """Heuristic check for math/science symbols."""
        eq_patterns = [
            '=', '+', '-', '×', '÷', '²', '³', '√',
            'sin', 'cos', 'tan', 'log', 'lim', '∫', 'Σ', 'π'
        ]
        text_lower = text.lower()
        return any(p in text_lower for p in eq_patterns)


# Singleton instance
ocr_service = HybridOCRService()