import csv
import os
from pyexpat.errors import messages
import shutil
import cv2
from datetime import timedelta, date 
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect, render
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q, F
from django.db.models.functions import TruncMonth
from django.urls import path, reverse

from django.contrib import messages
import csv, io

from .models import CustomUser, Attendance, LeaveRequest, FaceChangeRequest, UserFace, MasterUserRecord



# ---------------------------
# Custom Admin Site
# ---------------------------
class CustomAdminSite(admin.AdminSite):
    site_header = "AttendEase Administration"
    site_title = "AttendEase Admin"
    index_title = "Dashboard"
    

    # Custom URLs
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ajax/dashboard/', self.admin_view(self.ajax_dashboard_data), name='ajax_dashboard_data'),
            path('upload-master-data/', self.admin_view(self.upload_master_data_view), name='upload_master_data'),
        ]
        return custom_urls + urls




    def upload_master_data_view(self, request):
        if request.method == "POST":
            uploaded_file = request.FILES.get("file")
            if not uploaded_file:
                messages.error(request, "⚠️ Please select a CSV file to upload.")
                return redirect("admin:upload_master_data")
    
            # Read & decode the uploaded file
            file_bytes = uploaded_file.read()
            try:
                decoded_file = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                decoded_file = file_bytes.decode("latin-1")
    
            csv_buffer = io.StringIO(decoded_file, newline='')
            reader = csv.DictReader(csv_buffer)
    
            created_count = 0
            updated_count = 0
    
            for row in reader:
                username = (row.get("username") or "").strip()
                enrollment = (row.get("enrollment_no") or "").strip()
                email = (row.get("email") or "").strip()
                user_type = (row.get("user_type") or "student").strip().lower()
                face_path = (row.get("face_image") or "").strip()
    
                if not enrollment or not email:
                    continue
                
                from .models import MasterUserRecord
                record, created = MasterUserRecord.objects.update_or_create(
                    enrollment_no=enrollment,
                    defaults={
                        "username": username,
                        "email": email,
                        "user_type": user_type,
                    }
                )
    
                if face_path:
                    src_path = os.path.join(settings.MEDIA_ROOT, face_path)
                    dest_dir = os.path.join(settings.MEDIA_ROOT, "faces", username)
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, f"{username}_default.jpg")
    
                    if os.path.exists(src_path):
                        shutil.copy(src_path, dest_path)
                        record.face_image = f"faces/{username}/{username}_default.jpg"
                        record.save()
    
                if created:
                    created_count += 1
                else:
                    updated_count += 1
    
            messages.success(
                request,
                f"✅ Master data uploaded! ({created_count} created, {updated_count} updated)"
            )
            return redirect("admin:index")
    
        return render(request, "admin/upload_master_data.html", self.each_context(request))

    
    def index(self, request, extra_context=None):
        # CSV export (if requested)
        if request.GET.get('export') == 'csv':
            return self.export_attendance_csv()
    
        context = {
            **self.get_dashboard_context(request),
            **self.each_context(request),
        }
        return TemplateResponse(request, "admin/index.html", context)


    # ---------------------------
    # AJAX for real-time updates
    # ---------------------------
    def ajax_dashboard_data(self, request):
        context = self.get_dashboard_context(request)
        data = {
            'today_attendance': context['today_attendance'],
            'top_students': [
                {'username': u.username, 'attendance_percent': round(u.attendance_percent, 2)}
                for u in context['top_students']
            ],
            'top_faculty': [
                {'username': u.username, 'attendance_percent': round(u.attendance_percent, 2)}
                for u in context['top_faculty']
            ],
            'student_counts': context['student_counts'],
            'faculty_counts': context['faculty_counts'],
            'low_attendance_users': [
                {'username': u.username, 'user_type': u.user_type, 'attendance_percent': round(u.attendance_percent, 2)}
                for u in context['low_attendance_users']
            ],
        }
        return JsonResponse(data)

    # ---------------------------
    # Dashboard Context
    # ---------------------------
    def get_dashboard_context(self, request):
        today_total = Attendance.objects.filter(date= date.today()).count()
        total_users = CustomUser.objects.count()
        today_attendance_percent = round((today_total / total_users) * 100, 2) if total_users else 0

        total_students = CustomUser.objects.filter(user_type='student').count()
        total_faculty = CustomUser.objects.filter(user_type='faculty').count()

        # Top 3 students/faculty by attendance %
        top_students = (
            CustomUser.objects.filter(user_type='student')
            .annotate(
                present_days=Count('attendance', filter=Q(attendance__status='Present')),
                total_days=Count('attendance')
            )
            .annotate(attendance_percent=F('present_days') * 100.0 / F('total_days'))
            .order_by('-attendance_percent')[:3]
        )

        top_faculty = (
            CustomUser.objects.filter(user_type='faculty')
            .annotate(
                present_days=Count('attendance', filter=Q(attendance__status='Present')),
                total_days=Count('attendance')
            )
            .annotate(attendance_percent=F('present_days') * 100.0 / F('total_days'))
            .order_by('-attendance_percent')[:3]
        )

        # Monthly Attendance Charts
        student_monthly = (
            Attendance.objects.filter(user__user_type='student')
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        faculty_monthly = (
            Attendance.objects.filter(user__user_type='faculty')
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        months = [m['month'].strftime('%b') for m in student_monthly] or ['Jan','Feb','Mar','Apr','May']
        student_counts = [m['count'] for m in student_monthly] or [0,0,0,0,0]
        faculty_counts = [m['count'] for m in faculty_monthly] or [0,0,0,0,0]

        # Low Attendance <75%
        low_attendance_users = (
            CustomUser.objects.annotate(
                present_days=Count('attendance', filter=Q(attendance__status='Present')),
                total_days=Count('attendance')
            )
            .annotate(attendance_percent=F('present_days') * 100.0 / F('total_days'))
            .filter(attendance_percent__lt=75)
        )

        # Recent 5 attendance records
        attendance_by_status = Attendance.objects.select_related('user').order_by('-date')[:5]

        context = {
            **self.each_context(request),
            'total_students': total_students,
            'total_faculty': total_faculty,
            'today_attendance': today_attendance_percent,
            'top_students': top_students,
            'top_faculty': top_faculty,
            'months': months,
            'student_counts': student_counts,
            'faculty_counts': faculty_counts,
            'low_attendance_users': low_attendance_users,
            'attendance_by_status': attendance_by_status,
        }
        return context

    # ---------------------------
    # CSV Export
    # ---------------------------
    def export_attendance_csv(self):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attendance.csv"'
        import csv
        writer = csv.writer(response)
        writer.writerow(['Username','User Type','Date','Status','Check In','Check Out'])
        for att in Attendance.objects.select_related('user').all():
            writer.writerow([
                att.user.username,
                att.user.user_type,
                att.date,
                att.status,
                att.check_in if att.check_in else '--',
                att.check_out if att.check_out else '--'
            ])
        return response


# ---------------------------
# Create custom admin site instance
# ---------------------------

custom_admin_site = CustomAdminSite(name='custom_admin')


class MasterUserRecordAdmin(admin.ModelAdmin):
    list_display = ("username", "enrollment_no", "user_type", "email", "created_at")
    search_fields = ("username", "enrollment_no")

# ✅ Register with your custom admin site
custom_admin_site.register(MasterUserRecord, MasterUserRecordAdmin)

# ---------------------------
# CustomUser Admin
# ---------------------------
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "enrollment_no", "user_type", "is_approved", "has_face_data")
    list_filter = ("is_approved", "user_type", "has_face_data")
    actions = ["approve_users"]

    def approve_users(self, request, queryset):
        queryset.update(is_approved=True)
    approve_users.short_description = "Approve selected users"


custom_admin_site.register(CustomUser, CustomUserAdmin)


class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "check_in", "check_out", "status")
    search_fields = ("user__username", "user__enrollment_no")

    # Custom URLs
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "all-users-attendance/",
                self.admin_site.admin_view(self.all_users_attendance_view),
                name="all_users_attendance",
            ),
        ]
        return custom_urls + urls

    # Redirect changelist to custom view
    def changelist_view(self, request, extra_context=None):
        url = reverse('admin:all_users_attendance', current_app=self.admin_site.name)
        return redirect(url)

    def all_users_attendance_view(self, request):
        user_type_filter = request.GET.get("user_type", "")
        search_query = request.GET.get("search", "")
        export_type = request.GET.get("export")  # attendance / leave
        export_user_id = request.GET.get("user")  # optional single user

        users = CustomUser.objects.all().order_by("username")
        if user_type_filter:
            users = users.filter(user_type=user_type_filter)
        if search_query:
            users = users.filter(username__icontains=search_query)
        if export_user_id:
            users = users.filter(id=export_user_id)

        today = date.today()
        all_user_data = []

        for user in users:
            attendances = {att.date: att for att in Attendance.objects.filter(user=user)}
            leaves = LeaveRequest.objects.filter(user=user, status="Approved")

            # Collect leave dates
            leave_dates = set()
            for leave in leaves:
                curr = leave.start_date
                while curr <= leave.end_date:
                    leave_dates.add(curr)
                    curr += timedelta(days=1)

            start_date = user.date_joined.date()
            end_date = today

            user_records = []
            current = start_date
            while current <= end_date:
                if current in leave_dates:
                    status = "Leave"
                elif current.weekday() in (5,6):
                    status = "Holiday"
                elif current in attendances:
                    att = attendances[current]
                    if att.check_in and att.check_out:
                        status = "Present"
                    elif att.check_in:
                        status = "Present (Checked In Only)"
                    else:
                        status = "Absent"
                else:
                    status = "Absent"

                record = {
                    "date": current,
                    "status": status,
                    "check_in": attendances[current].check_in.strftime("%H:%M:%S") if current in attendances and attendances[current].check_in else "--",
                    "check_out": attendances[current].check_out.strftime("%H:%M:%S") if current in attendances and attendances[current].check_out else "--",
                }
                user_records.append(record)
                current += timedelta(days=1)

            total_days = len([r for r in user_records if r["status"] not in ("Holiday","Leave")])
            present_days = len([r for r in user_records if r["status"].startswith("Present")])
            absent_days = len([r for r in user_records if r["status"]=="Absent"])
            leave_days = len([r for r in user_records if r["status"]=="Leave"])
            holiday_days = len([r for r in user_records if r["status"]=="Holiday"])
            attendance_percentage = round((present_days / total_days) * 100, 2) if total_days else 0

            all_user_data.append({
                "user": user,
                "records": user_records[::-1],
                "present_days": present_days,
                "absent_days": absent_days,
                "leave_days": leave_days,
                "holiday_days": holiday_days,
                "attendance_percentage": attendance_percentage,
                "leaves": leaves,
            })

        # ----------------------------
        # CSV Export
        # ----------------------------
        if export_type in ("attendance", "leave"):
            import csv
            response = HttpResponse(content_type="text/csv")
            filename = f"{user.username}_data.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            writer = csv.writer(response)

            if export_type == "attendance":
                writer.writerow(["Username", "Enrollment No", "User Type", "Date", "Status", "Check In", "Check Out"])
                for data in all_user_data:
                    user = data["user"]
                    for record in data["records"]:
                        writer.writerow([
                            user.username,
                            user.enrollment_no or "--",
                            user.user_type,
                            record["date"].strftime("%Y-%m-%d"),
                            record["status"],
                            record["check_in"],
                            record["check_out"]
                        ])
            elif export_type == "leave":
                writer.writerow(["Username", "Enrollment No", "User Type", "From", "To", "Reason", "Status"])
                for data in all_user_data:
                    for l in data["leaves"]:
                        writer.writerow([
                            l.user.username,
                            l.user.enrollment_no or "--",
                            l.user.user_type,
                            l.start_date,
                            l.end_date,
                            l.reason,
                            l.status
                        ])
            return response

        # ----------------------------
        # Render HTML view
        # ----------------------------
        context = {
            "user_data": all_user_data,
            "user_type_filter": user_type_filter,
            "search_query": search_query,
        }
        return TemplateResponse(request,"admin/all_users_attendance.html",{**context,**self.admin_site.each_context(request),
        }
)

# Re    gister admin
custom_admin_site.register(Attendance, AttendanceAdmin)


# # ---------------------------
# # Attendance Admin
# # ---------------------------
# class AttendanceAdmin(admin.ModelAdmin):
#     list_display = ("user", "date", "check_in", "check_out", "status")
#     list_filter = ("status", "date")
#     search_fields = ("user__username", "user__enrollment_no")

#     def get_urls(self):
#         urls = super().get_urls()
#         custom_urls = [
#             path(
#                 "all-users-attendance/",
#                 self.admin_site.admin_view(self.all_users_attendance_view),
#                 name="all_users_attendance",
#             ),
#         ]
#         return custom_urls + urls

#     def all_users_attendance_view(self, request):
#         records = Attendance.objects.select_related("user").order_by("-date")
#         if request.GET.get("export") == "csv":
#             response = HttpResponse(content_type="text/csv")
#             response['Content-Disposition'] = 'attachment; filename="all_users_attendance.csv"'
#             import csv
#             writer = csv.writer(response)
#             writer.writerow(["Username","Enrollment No","User Type","Date","Check In","Check Out","Status"])
#             for r in records:
#                 writer.writerow([
#                     r.user.username,
#                     r.user.enrollment_no or "--",
#                     r.user.user_type,
#                     r.date.strftime("%Y-%m-%d"),
#                     r.check_in.strftime("%H:%M:%S") if r.check_in else "--",
#                     r.check_out.strftime("%H:%M:%S") if r.check_out else "--",
#                     r.status
#                 ])
#             return response
#         return render(request, "admin/all_users_attendance.html", {"records": records})


# custom_admin_site.register(Attendance, AttendanceAdmin)


# ---------------------------
# LeaveRequest Admin
# ---------------------------
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "user_type", "start_date", "end_date", "leave_type", "created_at", "status")
    list_filter = ("status", "leave_type", "user__user_type")
    search_fields = ("user__username", "user__enrollment_no")
    actions = ["approve_leaves", "reject_leaves"]

    def user_type(self, obj):
        return obj.user.user_type

    def approve_leaves(self, request, queryset):
        queryset.update(status="Approved")
    approve_leaves.short_description = "Approve selected leave requests"

    def reject_leaves(self, request, queryset):
        queryset.update(status="Rejected")
    reject_leaves.short_description = "Reject selected leave requests"


custom_admin_site.register(LeaveRequest, LeaveRequestAdmin)


class FaceChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "created_at", "preview_old", "preview_new")
    actions = ["approve_request", "reject_request"]

    def preview_old(self, obj):
        from .models import UserFace
        # Show latest approved face
        latest_face = UserFace.objects.filter(user=obj.user).order_by("-uploaded_at").first()
        if latest_face and latest_face.face_image:
            return format_html("<img src='{}' width='50'/>", latest_face.face_image.url)

        # Fallback: check default faces folder
        user_path = f"{settings.MEDIA_URL}faces/{obj.user.username}/{obj.user.username}_1.jpg"
        return format_html("<img src='{}' width='50'/>", user_path)
    preview_old.short_description = "Old Face"

    def preview_new(self, obj):
        # Only show pending face from request
        if hasattr(obj, "new_image") and obj.new_image:
            return format_html("<img src='{}' width='50'/>", obj.new_image.url)
        elif getattr(obj, "new_face_path", None):
            relative_path = obj.new_face_path.replace(str(settings.MEDIA_ROOT), "").lstrip("/")
            return format_html("<img src='{}{}' width='50'/>", settings.MEDIA_URL, relative_path)

        return "No Image"
    preview_new.short_description = "New Face"

    @admin.action(description="Approve selected face change requests")
    def approve_request(self, request, queryset):
        count = 0
        for obj in queryset:
            try:
                user = obj.user
                user_folder = os.path.join(settings.MEDIA_ROOT, "faces", user.username)
                os.makedirs(user_folder, exist_ok=True)
    
                # Determine source path of new face
                src_path = None
                if hasattr(obj, "new_image") and getattr(obj.new_image, "path", None):
                    src_path = obj.new_image.path
                elif getattr(obj, "new_face_path", None) and os.path.exists(obj.new_face_path):
                    src_path = obj.new_face_path
    
                if not src_path:
                    continue
                
                # Count existing images to create next number
                existing_files = [f for f in os.listdir(user_folder) if f.startswith(user.username) and f.endswith(".jpg")]
                next_index = len(existing_files) + 1
                dest_path = os.path.join(user_folder, f"{user.username}_{next_index}.jpg")
    
                # Copy new face
                shutil.copy(src_path, dest_path)
    
                # Update UserFace to latest approved
                from .models import UserFace
                UserFace.objects.update_or_create(
                    user=user,
                    defaults={"face_image": f"faces/{user.username}/{user.username}_{next_index}.jpg"}
                )
    
                # Mark request as approved
                obj.status = "Approved"
                obj.save()
                count += 1
    
            except Exception as e:
                self.message_user(request, f"Error approving {obj.user.username}: {str(e)}", messages.ERROR)
    
        self.message_user(request, f"{count} face change request(s) approved ✅", messages.SUCCESS)
    
    @admin.action(description="Reject selected face change requests")
    def reject_request(self, request, queryset):
        count = 0
        for obj in queryset:
            obj.status = "Rejected"
            obj.save()
            count += 1
        self.message_user(request, f"{count} face change request(s) rejected 🚫", messages.WARNING)

custom_admin_site.register(FaceChangeRequest, FaceChangeRequestAdmin)

class UserFaceAdmin(admin.ModelAdmin):
    list_display = ("user", "face_preview", "uploaded_at", "face_status")
    search_fields = ("user__username",)
    list_filter = ("uploaded_at",)

    def face_preview(self, obj):
        if obj.face_image:
            return format_html("<img src='{}' width='50'/>", obj.face_image.url)
        return "No Face"
    face_preview.short_description = "Face"

    def face_status(self, obj):
        # First-time face captured → status "Captured"
        # If no face yet → status "Pending"
        return "Captured" if obj.face_image else "Pending"
    face_status.short_description = "Status"

# Register the UserFace admin
custom_admin_site.register(UserFace, UserFaceAdmin)