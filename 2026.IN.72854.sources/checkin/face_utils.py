import base64
import binascii
import logging
import os
import tempfile

from django.core.files.base import ContentFile
from deepface import DeepFace


logger = logging.getLogger(__name__)


# ============================================================
# FACE IMAGE CONFIGURATION
# CẤU HÌNH ẢNH KHUÔN MẶT
# ============================================================

ALLOWED_IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
}

ALLOWED_CAPTURE_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
}

# Limit individual face images to 10 MB for the local demo.
# Giới hạn mỗi ảnh khuôn mặt tối đa 10 MB cho bản demo local.
MAX_FACE_IMAGE_SIZE = (
    10 * 1024 * 1024
)


# ============================================================
# TEMPORARY FILE HELPERS
# HÀM HỖ TRỢ FILE TẠM
# ============================================================

def remove_temp_file(temp_path):
    """
    Remove a temporary file without hiding the original error.
    Xóa file tạm nhưng không che mất lỗi gốc.
    """

    if not temp_path:
        return

    try:
        if os.path.exists(
            temp_path
        ):
            os.remove(
                temp_path
            )

    except OSError:
        # Cleanup failure should be logged but must not
        # replace the original Face Verification result/error.
        # Lỗi cleanup chỉ được ghi log, không được che
        # kết quả/lỗi Face Verification ban đầu.
        logger.warning(
            "Unable to remove temporary face image: %s",
            temp_path,
            exc_info=True,
        )


def save_django_file_to_temp(
    django_file,
):
    """
    Save a Django uploaded file or ContentFile
    to a temporary image file.

    Lưu Django uploaded file hoặc ContentFile
    thành file ảnh tạm.
    """

    if django_file is None:
        raise ValueError(
            "Image file is required."
        )

    file_name = getattr(
        django_file,
        "name",
        "",
    )

    if not file_name:
        raise ValueError(
            "Image file name is missing."
        )

    suffix = (
        os.path.splitext(
            file_name
        )[1]
        .lower()
    )

    # Do not silently rename unsupported files as JPG.
    # Không âm thầm đổi file không hỗ trợ thành JPG.
    if (
        suffix
        not in ALLOWED_IMAGE_SUFFIXES
    ):
        raise ValueError(
            "Face image must be a JPG, JPEG, or PNG file."
        )

    file_size = getattr(
        django_file,
        "size",
        None,
    )

    if (
        file_size is not None
        and file_size > MAX_FACE_IMAGE_SIZE
    ):
        raise ValueError(
            "Face image is too large."
        )

    # Reset the file pointer before reading.
    # Đưa con trỏ file về đầu trước khi đọc.
    try:
        django_file.seek(0)

    except (
        AttributeError,
        OSError,
    ):
        pass

    temp_path = None
    bytes_written = 0

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            temp_path = (
                temp_file.name
            )

            if hasattr(
                django_file,
                "chunks",
            ):
                for chunk in (
                    django_file.chunks()
                ):
                    bytes_written += len(
                        chunk
                    )

                    if (
                        bytes_written
                        > MAX_FACE_IMAGE_SIZE
                    ):
                        raise ValueError(
                            "Face image is too large."
                        )

                    temp_file.write(
                        chunk
                    )

            else:
                file_data = (
                    django_file.read()
                )

                if not file_data:
                    raise ValueError(
                        "The uploaded image is empty."
                    )

                if (
                    len(file_data)
                    > MAX_FACE_IMAGE_SIZE
                ):
                    raise ValueError(
                        "Face image is too large."
                    )

                bytes_written = len(
                    file_data
                )

                temp_file.write(
                    file_data
                )

        if bytes_written <= 0:
            raise ValueError(
                "The uploaded image is empty."
            )

        return temp_path

    except Exception:
        # Remove incomplete temporary data on failure.
        # Xóa file tạm chưa hoàn chỉnh nếu xảy ra lỗi.
        remove_temp_file(
            temp_path
        )

        raise


# ============================================================
# CAMERA BASE64 CONVERSION
# CHUYỂN ẢNH BASE64 TỪ CAMERA
# ============================================================

def base64_to_content_file(data):
    """
    Convert a camera Data URL into Django ContentFile.
    Chuyển Data URL từ camera thành Django ContentFile.
    """

    if not data:
        raise ValueError(
            "Captured image data is empty."
        )

    # Camera capture must provide an explicit Base64 Data URL.
    # Camera phải gửi Data URL Base64 có MIME rõ ràng.
    if ";base64," not in data:
        raise ValueError(
            "Invalid captured image format."
        )

    try:
        header, img_str = (
            data.split(
                ";base64,",
                1,
            )
        )

        if not header.startswith(
            "data:"
        ):
            raise ValueError(
                "Invalid captured image header."
            )

        mime_type = (
            header[
                len("data:"):
            ]
            .strip()
            .lower()
        )

        if (
            mime_type
            not in ALLOWED_CAPTURE_MIME_TYPES
        ):
            raise ValueError(
                "Unsupported captured image format."
            )

        extension = (
            ALLOWED_CAPTURE_MIME_TYPES[
                mime_type
            ]
        )

        decoded_file = (
            base64.b64decode(
                img_str,
                validate=True,
            )
        )

    except (
        ValueError,
        binascii.Error,
    ) as error:
        raise ValueError(
            "Invalid captured image data."
        ) from error

    if not decoded_file:
        raise ValueError(
            "Captured image is empty."
        )

    if (
        len(decoded_file)
        > MAX_FACE_IMAGE_SIZE
    ):
        raise ValueError(
            "Captured face image is too large."
        )

    return ContentFile(
        decoded_file,
        name=(
            f"captured_face."
            f"{extension}"
        ),
    )


# ============================================================
# FACE VERIFICATION
# XÁC MINH KHUÔN MẶT
# ============================================================

def verify_customer_face(
    registered_image_path,
    current_image_file,
):
    """
    Compare one registered reference face against
    the current check-in face.

    So sánh một ảnh khuôn mặt tham chiếu đã đăng ký
    với khuôn mặt hiện tại khi check-in.
    """

    if not registered_image_path:
        raise ValueError(
            "Registered face image path is missing."
        )

    if not os.path.isfile(
        registered_image_path
    ):
        raise FileNotFoundError(
            "Registered face image file was not found."
        )

    temp_current_image_path = (
        save_django_file_to_temp(
            current_image_file
        )
    )

    try:
        # DeepFace performs one-to-one Face Verification.
        # DeepFace thực hiện Face Verification một-một.
        result = DeepFace.verify(
            img1_path=(
                registered_image_path
            ),
            img2_path=(
                temp_current_image_path
            ),

            # Keep the recognition model used by this project.
            # Giữ recognition model đang dùng trong project.
            model_name="VGG-Face",

            # OpenCV detector is suitable for the local demo.
            # OpenCV detector phù hợp cho bản demo local.
            detector_backend="opencv",

            # Verification must fail when no valid face
            # can be detected.
            # Verification phải thất bại nếu không phát hiện
            # được khuôn mặt hợp lệ.
            enforce_detection=True,

            # Align detected faces before comparison.
            # Căn chỉnh khuôn mặt trước khi so sánh.
            align=True,
        )

        return {
            "verified": bool(
                result.get(
                    "verified",
                    False,
                )
            ),

            "distance": (
                result.get(
                    "distance"
                )
            ),

            "threshold": (
                result.get(
                    "threshold"
                )
            ),

            "model": (
                result.get(
                    "model",
                    "VGG-Face",
                )
            ),
        }

    finally:
        # Temporary current-face images are never kept
        # after verification.
        # Ảnh khuôn mặt hiện tại dạng temporary
        # không được giữ lại sau khi verification.
        remove_temp_file(
            temp_current_image_path
        )