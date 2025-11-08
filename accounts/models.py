from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings  
from django.contrib.auth import get_user_model


# Create your models here.

class CustomUser(AbstractUser):
    enrollment_no = models.CharField(max_length=11 , null=True , unique=True , blank=True)
    # institute_email = models.EmailField(unique=True)
    user_type = models.CharField(
        max_length=10,
        choices=(("student", "Student") , ("faculty", "Faculty")),
        default="student"
    )
    is_approved = models.BooleanField(default=False)  #For check wheather the user is approved or not
    has_face_data = models.BooleanField(default=False)  

class PendingFaceUpdate(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    new_image = models.ImageField(upload_to="pending_faces/")
    old_image = models.ImageField(upload_to="faces/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=[("Pending","Pending"), ("Approved","Approved"), ("Rejected","Rejected")], default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)    

class FaceChangeRequest(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    new_face_path = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)




class Attendance(models.Model):
    STATUS_CHOICES = [
        ("Present", "Present"),
        ("Absent", "Absent"),
        ("Checked In", "Checked In (No Check-Out)"),
        ("Holiday", "Holiday"),
        ("Leave", "Leave"),
    ]

    
    LEAVE_TYPE_CHOICES = [
    ("sick leave", "Sick Leave"),
    ("casual leave", "Casual Leave"),
    ("vacation", "Vacation"),
    ("emergency", "Emergency"),
    ("other", "Other"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Absent")
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, null=True, blank=True)
    

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.status})"


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    LEAVE_TYPE_CHOICES = Attendance.LEAVE_TYPE_CHOICES

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, default="Other")
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
        return f"{self.user.username} - {self.start_date} to {self.end_date} ({self.status})"

class UserFace(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    face_image = models.ImageField(upload_to="faces/%Y/%m/%d/", null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Face"
    
class MasterUserRecord(models.Model):
    username = models.CharField(max_length=150)
    enrollment_no = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=[("student", "Student"), ("faculty", "Faculty")])
    face_image = models.ImageField(upload_to="faces/master_faces/", blank=True, null=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.enrollment_no})"