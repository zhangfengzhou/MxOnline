# -*- coding:utf-8 -*-
import json
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.views.generic.base import View
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse

from pure_pagination import Paginator, PageNotAnInteger

from .models import UserProfile, EmailVerifyRecord, Banner
from .forms import LoginForm, RegisterForm, ForgetPwdForm, ModifyPwdForm, UploadImageForm, UserInfoForm
from operation.models import UserCourse, UserFavorite, UserMessage
from organization.models import CourseOrg, Teacher
from courses.models import Course
from utils.email_send import send_register_email
from utils.mixin_utils import LoginRequiredMixin


class CustomBackEnd(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        try:
            user = UserProfile.objects.get(Q(username=username) | Q(email=username))
            if user.check_password(password):
                return user
        except Exception as e:
            print e.message
            return None


class IndexView(View):
    def get(self, request):
        all_banners = Banner.objects.all().order_by('-index')
        banner_courses = Course.objects.filter(is_banner=True)[:3]
        all_courses = Course.objects.filter(is_banner=False)[:6]
        course_orgs = CourseOrg.objects.all()[:15]
        return render(request, 'index.html', {
            "all_banners": all_banners,
            "banner_courses": banner_courses,
            "all_courses": all_courses,
            "course_orgs": course_orgs
        })


class ModifyPwdView(View):
    def post(self, request):
        modifypwd_form = ModifyPwdForm(request.POST)
        if modifypwd_form.is_valid():
            password1 = request.POST.get("password1", "")
            password2 = request.POST.get("password2", "")
            email = request.POST.get("email", "")
            if password1 != password2:
                return render(request, "password_reset.html", {"email": email, "msg": "密码不一致"})
            user_profile = UserProfile.objects.get(email=email)
            user_profile.password = make_password(password1)
            user_profile.save()
            return render(request, "login.html")
        else:
            email = request.POST.get("email", "")
            return render(request, "password_reset.html", {"email": email, "modifypwd_form": modifypwd_form})


class ResetPwdView(View):
    def get(self, request, reset_code):
        all_records = EmailVerifyRecord.objects.filter(code=reset_code)
        if all_records:
            for record in all_records:
                email = record.email
                return render(request, "password_reset.html", {"email": email})
        else:
            return render(request, "activate_fail.html")
        return render(request, "login.html")


class ForgetPwdView(View):
    def get(self, request):
        forgetpwd_form = ForgetPwdForm()
        return render(request, "forgetpwd.html", {"forgetpwd_form": forgetpwd_form})

    def post(self, request):
        forgetpwd_form = ForgetPwdForm(request.POST)
        if forgetpwd_form.is_valid():
            email = request.POST.get("email", "")
            send_register_email(email=email, send_type="forgot")
            return render(request, "send_success.html")
        else:
            return render(request, "forgetpwd.html", {"forgetpwd_form": forgetpwd_form})


class ActivateUserView(View):
    def get(self, request, active_code):
        all_records = EmailVerifyRecord.objects.filter(code=active_code)
        if all_records:
            for record in all_records:
                email = record.email
                user = UserProfile.objects.get(email=email)
                user.is_active = True
                user.save()
        else:
            return render(request, "activate_fail.html")
        return render(request, "login.html")


class RegisterView(View):
    def get(self, request):
        register_form = RegisterForm()
        return render(request, "register.html", {"register_form": register_form})

    def post(self, request):
        register_form = RegisterForm(request.POST)
        if register_form.is_valid():
            user_name = request.POST.get("email", "")
            password = request.POST.get("password", "")
            if UserProfile.objects.filter(email=user_name):
                return render(request, "register.html", {"register_form": register_form, "msg": "用户已经存在"})
            user_profile = UserProfile()
            user_profile.username = user_name
            user_profile.email = user_name
            user_profile.is_active = False
            user_profile.password = make_password(password)
            user_profile.save()

            # 写入欢迎注册消息
            user_message = UserMessage()
            user_message.user = user_profile.id
            user_message.message = "欢迎注册慕学在线学习网"
            user_message.save()

            send_register_email(email=user_profile.email, send_type="register")
            return render(request, "login.html")
        else:
            return render(request, "register.html", {"register_form": register_form})


class LogoutView(View):
    def get(self, request):
        logout(request)
        # from django.core.urlresolvers import reverse
        # 重定向到index页面
        return HttpResponseRedirect(reverse('index'))


class LoginView(View):
    def get(self, request):
        return render(request, "login.html", {})

    def post(self, request):
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            user_name = request.POST.get("username", "")
            pass_word = request.POST.get("password", "")
            user = authenticate(username=user_name, password=pass_word)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    # 重定向到index页面
                    return HttpResponseRedirect(reverse('index'))
                else:
                    return render(request, "login.html", {"msg": "用户名未激活 "})
            else:
                return render(request, "login.html", {"msg": "用户名或密码错误 "})
        else:
            return render(request, "login.html", {"login_form": login_form})


# Create your views here.
# 下面这个是最初级的写法 没有通过View来写
def user_login(request):
    if request.method == "POST":
        user_name = request.POST.get("username", "")
        pass_word = request.POST.get("password", "")
        user = authenticate(username=user_name, password=pass_word)
        if user is not None:
            login(request, user)
            return render(request, "index.html", {})
        else:
            return render(request, "login.html", {"msg": "用户名或密码错误 "})
    elif request.method == "GET":
        return render(request, "login.html", {})


# 用户信息
class UserInfoView(LoginRequiredMixin, View):
    """
    用户信息
    """

    def get(self, request):
        return render(request, "usercenter-info.html", {})

    def post(self, request):
        user_info_form = UserInfoForm(request.POST, instance=request.user)
        if user_info_form.is_valid():
            user_info_form.save()
            return HttpResponse('{"status": "success"}', content_type='application/json')
        else:
            return HttpResponse(json.dumps(user_info_form.errors), content_type='application/json')


# 用户课程
class UserCoursesView(LoginRequiredMixin, View):
    def get(self, request):
        user_courses = UserCourse.objects.filter(user=request.user)
        return render(request, "usercenter-mycourse.html", {
            "user_courses": user_courses
        })


# 用户课程收藏
class UserFavCoursesView(LoginRequiredMixin, View):
    def get(self, request):
        course_list = []
        course_favs = UserFavorite.objects.filter(user=request.user, fav_type=1)
        for fav_course in course_favs:
            course_id = fav_course.fav_id
            course = Course.objects.get(id=course_id)
            course_list.append(course)
        return render(request, "usercenter-fav-course.html", {
            "course_list": course_list
        })


# 用户机构收藏
class UserFavOrgsView(LoginRequiredMixin, View):
    def get(self, request):
        org_list = []
        org_favs = UserFavorite.objects.filter(user=request.user, fav_type=2)
        for fav_org in org_favs:
            org_id = fav_org.fav_id
            org = CourseOrg.objects.get(id=org_id)
            org_list.append(org)
        return render(request, "usercenter-fav-org.html", {
            "org_list": org_list
        })


# 用户教师收藏
class UserFavTeachersView(LoginRequiredMixin, View):
    def get(self, request):
        teacher_list = []
        teacher_favs = UserFavorite.objects.filter(user=request.user, fav_type=3)
        for fav_teacher in teacher_favs:
            teacher_id = fav_teacher.fav_id
            teacher = Teacher.objects.get(id=teacher_id)
            teacher_list.append(teacher)
        return render(request, "usercenter-fav-teacher.html", {
            "teacher_list": teacher_list
        })


# 用户消息
class UserMessagesView(LoginRequiredMixin, View):
    def get(self, request):
        user_messages = UserMessage.objects.filter(user=request.user.id)
        all_unread_messages = UserMessage.objects.filter(user=request.user.id, has_read=False)
        for unread_message in all_unread_messages:
            unread_message.has_read = True
            unread_message.save()
        try:
            page = request.GET.get('page', 1)
        except PageNotAnInteger:
            page = 1
        # Provide Paginator with the request object for complete querystring generation
        p = Paginator(user_messages, 3, request=request)
        messages = p.page(page)
        return render(request, "usercenter-message.html", {
            "messages": messages
        })


# 用户头像上传处理
class UploadImageView(LoginRequiredMixin, View):
    def post(self, request):
        # 第一种写法
        # image_form = UploadImageForm(request.POST, request.FILES)
        # if image_form.is_valid():
        #     #  image = image_form.cleaned_data['image']
        #     #  request.user.image = image
        #     # request.user.save()

        # 第二种写法
        image_form = UploadImageForm(request.POST, request.FILES, instance=request.user)
        if image_form.is_valid():
            image_form.save()
            return HttpResponse('{"status": "success"}', content_type='application/json')
        else:
            return HttpResponse('{"status": "fail"}', content_type='application/json')


class UpdateUserPwdView(LoginRequiredMixin, View):
    """
    修改用户中心密码
    """

    def post(self, request):
        modifypwd_form = ModifyPwdForm(request.POST)
        if modifypwd_form.is_valid():
            password1 = request.POST.get("password1", "")
            password2 = request.POST.get("password2", "")
            if password1 != password2:
                return HttpResponse('{"status": "fail", "msg":"密码不一致"}', content_type='application/json')
            user = request.user
            user.password = make_password(password1)
            user.save()
            return HttpResponse('{"status": "success"}', content_type='application/json')
        else:
            return HttpResponse(json.dumps(modifypwd_form.errors), content_type='application/json')


class SendEmailCodeView(LoginRequiredMixin, View):
    """
    发送修改邮箱验证码
    """

    def get(self, request):
        email = request.GET.get('email', '')
        if UserProfile.objects.filter(email=email):
            return HttpResponse('{"email": "邮箱已存在"}', content_type='application/json')
        send_register_email(email, send_type='update_email')
        return HttpResponse('{"status": "success"}', content_type='application/json')


class UpdateEmailView(LoginRequiredMixin, View):
    """
    修改邮箱
    """

    def post(self, request):
        email = request.POST.get('email', '')
        code = request.POST.get('code', '')
        existed_recored = EmailVerifyRecord.objects.filter(email=email, code=code, send_type='update_email')
        if existed_recored:
            # 修改用户邮箱
            user = request.user
            user.email = email
            user.save()
            return HttpResponse('{"status": "success"}', content_type='application/json')
        else:
            return HttpResponse('{"email": "验证码错误"}', content_type='application/json')


def page_not_fount(request):
    from django.shortcuts import render_to_response
    response = render_to_response('404.html', {})
    response.status_code = 404
    return response


def page_server_error(request):
    from django.shortcuts import render_to_response
    response = render_to_response('500.html', {})
    response.status_code = 500
    return response
