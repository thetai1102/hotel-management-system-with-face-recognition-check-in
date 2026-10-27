from django.db import models


class Customer(models.Model):
    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    id_card_number = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True, null=True)

    # Old field, keep it so old code does not break.
    # Trường cũ, giữ lại để code cũ không lỗi.
    face_image = models.ImageField(
        upload_to='customer_faces/',
        blank=True,
        null=True
    )

    # New workflow fields.
    # Ảnh giấy tờ và ảnh selfie khách upload khi đặt phòng online.
    id_document_image = models.ImageField(
        upload_to='customer_documents/',
        blank=True,
        null=True
    )

    selfie_image = models.ImageField(
        upload_to='customer_selfies/',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def get_reference_face(self):
        """
        Return selfie image first. If not available, use old face_image.
        Ưu tiên dùng selfie_image, nếu chưa có thì dùng face_image cũ.
        """
        if self.selfie_image:
            return self.selfie_image

        return self.face_image

    def __str__(self):
        return self.full_name