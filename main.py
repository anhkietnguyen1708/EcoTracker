import os
import subprocess
import time
import shutil
import hashlib
import random

# IMPORT THƯ VIỆN GỌI API AWS
import requests

from PIL import Image as PILImage
from kivy.config import Config
from kivy.utils import platform
from kivy.core.window import Window

# 1. THIẾT LẬP CẤU HÌNH MÀN HÌNH CHUẨN ĐIỆN THOẠI DỌC (360x760)
if platform != 'android' and platform != 'ios':
    Window.size = (360, 760)

from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFillRoundFlatIconButton, MDFillRoundFlatButton, MDRoundFlatButton
from kivy.uix.camera import Camera
from kivy.graphics import Rotate, PushMatrix, PopMatrix, Color, Line, Ellipse, RoundedRectangle
from kivymd.uix.card import MDCard
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget
from kivy.properties import ListProperty, NumericProperty, StringProperty, BooleanProperty
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.progressbar import MDProgressBar

try:
    import cv2
    import numpy as np
except ImportError:
    print("Cảnh báo: Thiếu thư viện OpenCV hoặc Numpy.")


# ==========================================
# CÁC WIDGET VẼ BIỂU ĐỒ & CUSTOM WIDGETS
# ==========================================
class DonutChart(Widget):
    value = NumericProperty(84)

    def on_size(self, *args):
        self._draw_chart()

    def on_value(self, *args):
        self._draw_chart()

    def _draw_chart(self):
        self.canvas.clear()
        if self.width == 0 or self.height == 0:
            return
        with self.canvas:
            Color(0.8, 0.85, 0.8, 1)
            Line(circle=(self.center_x, self.center_y, self.width / 2.5, -135, 135), width=10, cap='round')
            Color(0.48, 0.65, 0.48, 1)
            safe_value = min(100, max(0, self.value))
            angle = -135 + (270 * (safe_value / 100))
            Line(circle=(self.center_x, self.center_y, self.width / 2.5, -135, angle), width=10, cap='round')


class HabitDonutChart(Widget):
    def on_size(self, *args):
        self.canvas.clear()
        if self.width == 0 or self.height == 0:
            return
        with self.canvas:
            Color(0.8, 0.85, 0.8, 1)
            Line(circle=(self.center_x, self.center_y, self.width / 2.5), width=12)
            angles = [0, 144, 252, 324, 360]
            colors = [(0.25, 0.5, 0.25, 1), (0.4, 0.65, 0.4, 1), (0.55, 0.75, 0.55, 1), (0.7, 0.85, 0.7, 1)]
            for i in range(4):
                Color(*colors[i])
                Line(circle=(self.center_x, self.center_y, self.width / 2.5, angles[i], angles[i + 1]), width=12)


class SmoothLineChart(Widget):
    data = ListProperty([60, 65, 55, 75, 80, 78, 85, 84, 90, 88])

    def on_size(self, *args):
        self.canvas.clear()
        if not self.data or self.width == 0:
            return
        step_x = self.width / (len(self.data) - 1)
        scale_y = self.height / 100
        points = []
        for i, val in enumerate(self.data):
            points.extend([self.x + i * step_x, self.y + val * scale_y])
        with self.canvas:
            Color(0.48, 0.65, 0.48, 1)
            Line(points=points, width=2, cap='round', joint='round')


class LineChart(Widget):
    data = ListProperty([4.2, 3.8, 5.1, 3.2, 2.9, 2.1, 3.4])
    max_val = NumericProperty(8)

    def on_size(self, *args):
        self.canvas.clear()
        if not self.data or self.width == 0:
            return
        step_x = self.width / (len(self.data) - 1)
        scale_y = self.height / self.max_val
        points = []
        for i, val in enumerate(self.data):
            points.extend([self.x + i * step_x, self.y + val * scale_y])
        with self.canvas:
            Color(0.8, 0.85, 0.8, 1)
            Line(points=[self.x, self.y + 5 * scale_y, self.right, self.y + 5 * scale_y], width=1.5, dash_offset=5, dash_length=5)
            Color(0.48, 0.65, 0.48, 1)
            Line(points=points, width=2)
            for i in range(len(self.data)):
                Ellipse(pos=(points[i * 2] - 4, points[i * 2 + 1] - 4), size=(8, 8))


class BarChart(Widget):
    data = ListProperty([60, 70, 68, 85])
    max_val = NumericProperty(100)

    def on_size(self, *args):
        self.canvas.clear()
        if not self.data or self.width == 0:
            return
        bar_width = (self.width / len(self.data)) * 0.4
        spacing = (self.width / len(self.data)) * 0.6
        scale_y = self.height / self.max_val
        with self.canvas:
            Color(0.48, 0.65, 0.48, 1)
            for i, val in enumerate(self.data):
                x = self.x + i * (bar_width + spacing) + spacing / 2
                y = self.y
                h = val * scale_y
                RoundedRectangle(pos=(x, y), size=(bar_width, h), radius=[8, 8, 8, 8])


UPLOAD_CACHE_DIR = "upload_cache"
if os.path.exists(UPLOAD_CACHE_DIR) and not os.path.isdir(UPLOAD_CACHE_DIR):
    os.remove(UPLOAD_CACHE_DIR)
if not os.path.exists(UPLOAD_CACHE_DIR):
    os.makedirs(UPLOAD_CACHE_DIR)


class SafeAnchorLayout(AnchorLayout):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            super(SafeAnchorLayout, self).on_touch_down(touch)
            return True
        return super(SafeAnchorLayout, self).on_touch_down(touch)


# ==========================================
# DANH SÁCH TASK TỔNG (POOL) - mỗi ngày random ra 3 task
# ==========================================
DAILY_TASKS_POOL = [
    {"title": "Tái sử dụng túi vải", "desc": "Chụp ảnh bạn dùng túi vải khi đi chợ/siêu thị", "icon": "shopping"},
    {"title": "Phân loại rác", "desc": "Chụp ảnh rác đã được phân loại tại nhà", "icon": "recycle"},
    {"title": "Tắt thiết bị điện không dùng", "desc": "Chụp ảnh thiết bị điện đã được tắt/rút phích cắm", "icon": "power-plug-off"},
    {"title": "Đạp xe / đi bộ", "desc": "Chụp ảnh hành trình đạp xe hoặc đi bộ thay vì xe máy", "icon": "bike"},
    {"title": "Tiết kiệm nước", "desc": "Chụp ảnh hành động tiết kiệm nước (khóa vòi, hứng nước...)", "icon": "water-outline"},
    {"title": "Trồng cây xanh", "desc": "Chụp ảnh cây xanh bạn vừa trồng hoặc chăm sóc", "icon": "sprout"},
    {"title": "Mang theo bình nước cá nhân", "desc": "Chụp ảnh bình nước cá nhân thay vì chai nhựa dùng 1 lần", "icon": "bottle-soda-classic"},
    {"title": "Tái chế đồ cũ", "desc": "Chụp ảnh một món đồ bạn đã tái chế/tái sử dụng", "icon": "recycle-variant"},
    {"title": "Ăn chay 1 bữa", "desc": "Chụp ảnh bữa ăn chay/giảm thịt trong ngày", "icon": "food-apple"},
    {"title": "Dọn rác nơi công cộng", "desc": "Chụp ảnh khu vực bạn vừa dọn dẹp rác", "icon": "broom"},
]


KV = '''
#:import get_color_from_hex kivy.utils.get_color_from_hex

<ActiveChallenge@MDCard>:
    size_hint_y: None
    height: "150dp"
    radius: [15]
    padding: "15dp"
    spacing: "8dp"
    md_bg_color: (0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
    elevation: 0
    orientation: "vertical"
    c_title: "Challenge"
    c_sub: "Sub"
    c_icon: "recycle"
    c_prog_text: "0/30 days"
    c_prog_val: 0
    c_tag: "500 XP"
    BoxLayout:
        orientation: "horizontal"
        spacing: "10dp"
        size_hint_y: None
        height: "50dp"
        MDIcon:
            icon: root.c_icon
            theme_text_color: "Custom"
            text_color: 0.1, 0.6, 0.1, 1
            size_hint_x: None
            width: "30dp"
            pos_hint: {"center_y": .5}
        BoxLayout:
            orientation: "vertical"
            spacing: "2dp"
            MDLabel:
                text: root.c_title
                bold: True
                font_style: "Subtitle2"
            MDLabel:
                text: root.c_sub
                font_style: "Caption"
                theme_text_color: "Secondary"
    BoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: "20dp"
        MDLabel:
            text: root.c_prog_text
            font_style: "Caption"
            theme_text_color: "Hint"
        MDLabel:
            text: f"{root.c_prog_val}%"
            font_style: "Caption"
            bold: True
            halign: "right"
    MDProgressBar:
        value: root.c_prog_val
        color: 0.4, 0.6, 0.4, 1
        size_hint_y: None
        height: "5dp"
    BoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: "30dp"
        BoxLayout:
            size_hint_x: None
            width: "100dp"
            padding: "2dp"
            canvas.before:
                Color:
                    rgba: (0.8, 0.85, 0.8, 1) if app.theme_cls.theme_style == "Light" else (0.3, 0.3, 0.3, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [10]
            MDIcon:
                icon: "trophy"
                theme_text_color: "Custom"
                text_color: 0.8, 0.6, 0, 1
                size_hint_x: None
                width: "25dp"
                halign: "center"
            MDLabel:
                text: root.c_tag
                font_style: "Caption"
                font_size: "10sp"
                bold: True
        Widget:

# ==========================================
# CÁC COMPONENT MỚI CHO ROADMAP TIẾN TRÌNH (Bản nâng cấp 10 cột mốc)
# ==========================================
<RoadmapNode@BoxLayout>:
    orientation: "vertical"
    size_hint: None, None
    size: "70dp", "90dp"
    spacing: "4dp"
    node_name: ""
    node_points: ""
    node_icon: "leaf"
    is_unlocked: False
    
    AnchorLayout:
        anchor_x: "center"
        anchor_y: "center"
        size_hint_y: None
        height: "40dp"
        Widget:
            size_hint: None, None
            size: "34dp", "36dp"
            canvas.before:
                Color:
                    rgba: (0.18, 0.49, 0.2, 1) if root.is_unlocked else (0.6, 0.6, 0.6, 0.4)
                Line:
                    circle: (self.center_x, self.center_y, 16)
                    width: 2
                Color:
                    rgba: (0.82, 0.88, 0.82, 1) if root.is_unlocked else (0.3, 0.3, 0.3, 0.1)
                Ellipse:
                    pos: self.center_x - 15, self.center_y - 15
                    size: 30, 30
        MDIcon:
            icon: root.node_icon
            halign: "center"
            valign: "center"
            font_size: "18sp"
            theme_text_color: "Custom"
            text_color: (0.18, 0.49, 0.2, 1) if root.is_unlocked else (0.6, 0.6, 0.6, 0.5)
    MDLabel:
        text: root.node_name
        halign: "center"
        font_style: "Caption"
        font_size: "8sp"
        bold: True
        theme_text_color: "Primary" if root.is_unlocked else "Hint"
    MDLabel:
        text: f"{root.node_points} XP"
        halign: "center"
        font_style: "Caption"
        font_size: "8sp"
        theme_text_color: "Hint"

<TimelineConnector@Widget>:
    size_hint: None, None
    size: "30dp", "3dp"
    pos_hint: {"center_y": .73}
    progress_val: 0.0
    canvas.before:
        # Đường nền màu xám
        Color:
            rgba: (0.6, 0.6, 0.6, 0.3)
        Rectangle:
            pos: self.pos
            size: self.size
        # Đường màu xanh chạy đè lên theo tỷ lệ tiến trình
        Color:
            rgba: (0.18, 0.49, 0.2, 1)
        Rectangle:
            pos: self.pos
            size: self.width * root.progress_val, self.height

# ==========================================
<TrophyItem@MDCard>:
    orientation: "vertical"
    unlocked: False
    icon: "leaf"
    title: ""
    desc: ""
    current_p: 0
    max_p: 100
    ripple_behavior: True
    radius: [15]
    elevation: 0
    md_bg_color: (0.85, 0.89, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.25, 0.25, 0.25, 1)
    on_release: app.show_trophy_details(self.title, self.icon, self.desc, self.unlocked, self.current_p, self.max_p)
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: (0.3, 0.7, 0.3, 1) if root.unlocked else (0.6, 0.6, 0.6, 0.3)
        halign: "center"
        valign: "center"
        font_size: "30sp"
        size_hint_y: 0.7
    MDLabel:
        text: root.title
        halign: "center"
        font_style: "Caption"
        font_size: "10sp"
        theme_text_color: "Secondary" if root.unlocked else "Hint"
        size_hint_y: 0.3

<BadgeItem@BoxLayout>:
    orientation: "vertical"
    unlocked: False
    icon: "leaf"
    title: "Badge"
    canvas.before:
        Color:
            rgba: (0.85, 0.89, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [15]
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: (0.3, 0.7, 0.3, 1) if root.unlocked else (0.6, 0.6, 0.6, 0.3)
        halign: "center"
        valign: "center"
        font_size: "24sp"
    MDLabel:
        text: root.title
        halign: "center"
        font_style: "Caption"
        font_size: "10sp"
        theme_text_color: "Secondary" if root.unlocked else "Hint"
        size_hint_y: None
        height: "20dp"
    MDIcon:
        icon: "circle"
        font_size: "10sp"
        halign: "center"
        theme_text_color: "Custom"
        text_color: (0.4, 0.6, 0.4, 1) if root.unlocked else (0, 0, 0, 0)

<SocialFeedItem@MDCard>:
    orientation: "vertical"
    padding: "10dp"
    spacing: "5dp"
    size_hint_y: None
    height: "100dp"
    radius: [15]
    elevation: 0
    md_bg_color: (0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
    user_name: "Tên"
    action_text: "Hành động"
    like_count: "0"
    BoxLayout:
        orientation: "horizontal"
        MDLabel:
            text: f"[b]{root.user_name}[/b] {root.action_text}"
            markup: True
            font_style: "Caption"
            theme_text_color: "Primary"
    BoxLayout:
        orientation: "horizontal"
        spacing: "10dp"
        size_hint_y: None
        height: "30dp"
        MDIconButton:
            icon: "heart-outline"
            theme_text_color: "Custom"
            text_color: 0.6, 0.6, 0.6, 1
            on_release: app.add_like(self, root)
        MDLabel:
            id: like_label
            text: f"{root.like_count} Thích"
            font_style: "Caption"
            theme_text_color: "Secondary"

<SidebarButton@MDFillRoundFlatIconButton>:
    text_color: (0.2, 0.2, 0.2, 1) if app.theme_cls.theme_style == "Light" else (0.8, 0.9, 0.8, 1)
    icon_color: (0.3, 0.5, 0.3, 1) if app.theme_cls.theme_style == "Light" else (0.5, 0.8, 0.5, 1)
    md_bg_color: 0, 0, 0, 0
    size_hint_x: 1
    anchor_x: "left"
    icon_pad: "12dp"
    font_size: "14sp"
    radius: [8, 8, 8, 8]

<CustomProgressBar@Widget>:
    value: 0
    canvas.before:
        Color:
            rgba: (0.8, 0.85, 0.8, 1) if app.theme_cls.theme_style == "Light" else (0.3, 0.3, 0.3, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height / 2]
        Color:
            rgba: 0.4, 0.6, 0.4, 1
        RoundedRectangle:
            pos: self.pos
            size: (self.width * (self.value / 100.0), self.height) if self.value > 0 else (0, self.height)
            radius: [self.height / 2]

<TeamLeaderboardItem@BoxLayout>:
    size_hint_y: None
    height: "60dp"
    spacing: "10dp"
    padding: "5dp"
    rank_text: "1"
    user_name: "Name"
    user_xp: "0 XP"
    progress_val: 0
    is_me: False
    canvas.before:
        Color:
            rgba: (0.82, 0.88, 0.8, 0.6) if root.is_me and app.theme_cls.theme_style == "Light" else ((0.3, 0.4, 0.3, 0.6) if root.is_me else (0, 0, 0, 0))
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [15]
    MDLabel:
        text: root.rank_text
        bold: True
        font_style: "Subtitle2"
        size_hint_x: None
        width: "25dp"
        halign: "center"
        theme_text_color: "Custom"
        text_color: (0.4, 0.6, 0.4, 1) if root.rank_text in ["1", "2", "3"] else (0.6, 0.6, 0.6, 1)
    MDIcon:
        icon: "account-circle"
        theme_text_color: "Custom"
        text_color: 0.4, 0.5, 0.4, 1
        font_size: "30sp"
        size_hint_x: None
        width: "35dp"
    BoxLayout:
        orientation: "vertical"
        size_hint_x: 0.5
        MDLabel:
            text: root.user_name
            bold: True
            font_style: "Caption"
            theme_text_color: "Primary"
        MDLabel:
            text: root.user_xp
            font_style: "Caption"
            theme_text_color: "Hint"
    AnchorLayout:
        anchor_x: "right"
        anchor_y: "center"
        size_hint_x: 0.5
        CustomProgressBar:
            size_hint: None, None
            size: "60dp", "8dp"
            value: root.progress_val

<StatCard@MDCard>:
    orientation: "vertical"
    padding: "10dp"
    spacing: "5dp"
    radius: [15]
    elevation: 0
    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
    icon: "leaf"
    value: "0"
    desc: "Desc"
    MDIcon:
        icon: root.icon
        halign: "center"
        font_size: "24sp"
        theme_text_color: "Custom"
        text_color: 0.4, 0.6, 0.4, 1
        canvas.before:
            Color:
                rgba: (0.82, 0.88, 0.82, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.3, 0.2, 1)
            Ellipse:
                pos: self.center_x - 20, self.center_y - 20
                size: 40, 40
    MDLabel:
        text: root.value
        halign: "center"
        font_style: "Subtitle1"
        bold: True
        theme_text_color: "Primary"
    MDLabel:
        text: root.desc
        halign: "center"
        font_style: "Caption"
        font_size: "10sp"
        theme_text_color: "Hint"

<GoalItem@BoxLayout>:
    orientation: "vertical"
    size_hint_y: None
    height: "40dp"
    title: ""
    progress_text: ""
    value: 0
    BoxLayout:
        MDLabel:
            text: root.title
            font_style: "Caption"
            font_size: "10sp"
            theme_text_color: "Primary"
        MDLabel:
            text: root.progress_text
            font_style: "Caption"
            font_size: "10sp"
            halign: "right"
            bold: True
            theme_text_color: "Hint"
    CustomProgressBar:
        size_hint_y: None
        height: "6dp"
        value: root.value

<PrefItem@MDCard>:
    orientation: "horizontal"
    padding: "10dp"
    spacing: "10dp"
    radius: [15]
    elevation: 0
    size_hint_y: None
    height: "50dp"
    md_bg_color: (0.85, 0.89, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
    icon: "clock"
    title: "Title"
    value: "Value"
    MDIcon:
        icon: root.icon
        pos_hint: {"center_y": .5}
        theme_text_color: "Custom"
        text_color: 0.4, 0.6, 0.4, 1
    BoxLayout:
        orientation: "vertical"
        MDLabel:
            text: root.title
            font_style: "Caption"
            theme_text_color: "Hint"
        MDLabel:
            text: root.value
            font_style: "Caption"
            bold: True
            theme_text_color: "Primary"

<DailyTaskItem@MDCard>:
    orientation: "horizontal"
    padding: "12dp"
    spacing: "10dp"
    radius: [15]
    elevation: 0
    size_hint_y: None
    height: "70dp"
    ripple_behavior: True
    task_index: 0
    icon: "leaf"
    title: "Task"
    desc: "Desc"
    completed: False
    md_bg_color: (0.85, 0.92, 0.85, 1) if root.completed else ((0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1))
    on_release: app.open_task_upload(root.task_index) if not root.completed else None
    MDIcon:
        icon: ("check-circle" if root.completed else root.icon)
        theme_text_color: "Custom"
        text_color: (0.2, 0.65, 0.2, 1) if root.completed else (0.25, 0.45, 0.25, 1)
        size_hint_x: None
        width: "32dp"
        font_size: "26sp"
        pos_hint: {"center_y": .5}
    BoxLayout:
        orientation: "vertical"
        spacing: "2dp"
        MDLabel:
            text: root.title
            bold: True
            font_style: "Subtitle2"
            theme_text_color: "Primary"
        MDLabel:
            text: ("Đã hoàn thành" if root.completed else root.desc)
            font_style: "Caption"
            font_size: "10sp"
            theme_text_color: "Hint" if not root.completed else "Custom"
            text_color: 0.2, 0.6, 0.2, 1
    MDIcon:
        icon: "chevron-right" if not root.completed else "lock-check"
        theme_text_color: "Custom"
        text_color: 0.6, 0.6, 0.6, 1
        size_hint_x: None
        width: "20dp"
        pos_hint: {"center_y": .5}

# =========================================================================
ScreenManager:
    id: main_screen_manager

    Screen:
        name: "login_screen"
        canvas.before:
            Color:
                rgba: (0.93, 0.96, 0.92, 1) if app.theme_cls.theme_style == "Light" else (0.1, 0.1, 0.1, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        AnchorLayout:
            anchor_x: "center"
            anchor_y: "center"
            MDCard:
                size_hint: 0.9, None
                height: "450dp"
                padding: "20dp"
                spacing: "15dp"
                orientation: "vertical"
                radius: [20]
                elevation: 4
                md_bg_color: app.theme_cls.bg_light
                BoxLayout:
                    orientation: "horizontal"
                    size_hint_y: None
                    height: "50dp"
                    spacing: "10dp"
                    pos_hint: {"center_x": 0.5}
                    MDIcon:
                        icon: "leaf"
                        text_color: 0.18, 0.49, 0.2, 1
                        theme_text_color: "Custom"
                        font_size: "35sp"
                    MDLabel:
                        text: "Eco Space"
                        bold: True
                        font_style: "H5"
                        theme_text_color: "Primary"
                MDLabel:
                    text: "Quản lý lối sống xanh"
                    font_style: "Caption"
                    halign: "center"
                    theme_text_color: "Secondary"
                Widget:
                    size_hint_y: None
                    height: "10dp"
                MDTextField:
                    id: login_user
                    hint_text: "Tên đăng nhập"
                    text: "Aria Chen"
                    icon_right: "account"
                    mode: "rectangle"
                MDTextField:
                    id: login_pass
                    hint_text: "Mật khẩu"
                    text: "********"
                    icon_right: "key"
                    password: True
                    mode: "rectangle"
                Widget:
                    size_hint_y: None
                    height: "10dp"
                MDFillRoundFlatButton:
                    text: "ĐĂNG NHẬP"
                    size_hint_x: 1
                    md_bg_color: 0.18, 0.49, 0.2, 1
                    radius: [8, 8, 8, 8]
                    on_release: app.process_login()

    Screen:
        name: "main_app_screen"
        MDNavigationLayout:

            ScreenManager:
                Screen:
                    BoxLayout:
                        orientation: "vertical"

                        # -- TOP APP BAR (MOBILE STYLE) --
                        MDTopAppBar:
                            id: top_app_bar
                            title: "Dashboard"
                            elevation: 4
                            pos_hint: {"top": 1}
                            md_bg_color: 0.18, 0.49, 0.2, 1
                            left_action_items: [["menu", lambda x: nav_drawer.set_state("open")]]

                        # -- NỘI DUNG CHÍNH --
                        ScreenManager:
                            id: sm

                            # === 1. DASHBOARD CHÍNH ===
                            Screen:
                                name: "tab_dashboard"
                                ScrollView:
                                    BoxLayout:
                                        orientation: "vertical"
                                        spacing: "15dp"
                                        padding: "10dp"
                                        size_hint_y: None
                                        height: self.minimum_height

                                        MDCard:
                                            radius: [15]
                                            size_hint_y: None
                                            height: "220dp"
                                            padding: "15dp"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0
                                            orientation: "vertical"

                                            BoxLayout:
                                                orientation: "horizontal"
                                                size_hint_y: None
                                                height: "30dp"
                                                MDLabel:
                                                    text: "Daily Eco Score"
                                                    font_style: "Subtitle2"
                                                    bold: True
                                                    theme_text_color: "Primary"
                                                MDRoundFlatButton:
                                                    text: "Top 15%"
                                                    font_size: "10sp"
                                                    size_hint_y: None
                                                    height: "25dp"
                                                    line_color: 0, 0, 0, 0
                                                    md_bg_color: 0.8, 0.85, 0.8, 1
                                                    text_color: 0.3, 0.5, 0.3, 1

                                            AnchorLayout:
                                                anchor_x: "center"
                                                anchor_y: "center"
                                                DonutChart:
                                                    id: donut_chart
                                                    size_hint: None, None
                                                    size: "100dp", "100dp"
                                                    value: 84
                                                BoxLayout:
                                                    orientation: "vertical"
                                                    size_hint: None, None
                                                    size: "60dp", "60dp"
                                                    MDLabel:
                                                        id: eco_score_label
                                                        text: "84"
                                                        font_style: "H5"
                                                        bold: True
                                                        halign: "center"
                                                        theme_text_color: "Custom"
                                                        text_color: (0, 0, 0, 1) if app.theme_cls.theme_style == "Light" else (1, 1, 1, 1)
                                                    MDLabel:
                                                        text: "Score"
                                                        font_style: "Caption"
                                                        font_size: "10sp"
                                                        halign: "center"
                                                        theme_text_color: "Hint"

                                            BoxLayout:
                                                orientation: "horizontal"
                                                size_hint_y: None
                                                height: "50dp"
                                                spacing: "5dp"

                                                MDCard:
                                                    radius: [10]
                                                    md_bg_color: (0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
                                                    elevation: 0
                                                    orientation: "vertical"
                                                    padding: "2dp"
                                                    MDLabel:
                                                        text: "3.4kg"
                                                        font_style: "Caption"
                                                        bold: True
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "Carbon"
                                                        font_style: "Caption"
                                                        font_size: "10sp"
                                                        halign: "center"
                                                        theme_text_color: "Hint"

                                                MDCard:
                                                    radius: [10]
                                                    md_bg_color: (0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
                                                    elevation: 0
                                                    orientation: "vertical"
                                                    padding: "2dp"
                                                    MDLabel:
                                                        text: "87L"
                                                        font_style: "Caption"
                                                        bold: True
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "Water"
                                                        font_style: "Caption"
                                                        font_size: "10sp"
                                                        halign: "center"
                                                        theme_text_color: "Hint"

                                                MDCard:
                                                    radius: [10]
                                                    md_bg_color: (0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
                                                    elevation: 0
                                                    orientation: "vertical"
                                                    padding: "2dp"
                                                    MDLabel:
                                                        text: "4.2kWh"
                                                        font_style: "Caption"
                                                        bold: True
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "Energy"
                                                        font_style: "Caption"
                                                        font_size: "10sp"
                                                        halign: "center"
                                                        theme_text_color: "Hint"

                                        # ---- DAILY TASKS (random 3 task / ngày) & NÚT NHẬN THƯỞNG ----
                                        MDCard:
                                            radius: [15]
                                            size_hint_y: None
                                            height: self.minimum_height
                                            padding: "15dp"
                                            spacing: "10dp"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0
                                            orientation: "vertical"
                                            BoxLayout:
                                                orientation: "horizontal"
                                                size_hint_y: None
                                                height: "25dp"
                                                MDLabel:
                                                    text: "Nhiệm vụ hôm nay"
                                                    bold: True
                                                    font_style: "Subtitle2"
                                                MDLabel:
                                                    id: daily_tasks_progress_label
                                                    text: "0/3 hoàn thành"
                                                    font_style: "Caption"
                                                    halign: "right"
                                                    theme_text_color: "Hint"
                                            BoxLayout:
                                                id: daily_tasks_box
                                                orientation: "vertical"
                                                spacing: "8dp"
                                                size_hint_y: None
                                                height: self.minimum_height
                                            
                                            # NÚT NHẬN THƯỞNG 200 XP (Ẩn đi theo mặc định)
                                            MDFillRoundFlatButton:
                                                id: claim_bonus_btn
                                                text: "🎉 NHẬN 200 XP THƯỞNG"
                                                font_size: "12sp"
                                                pos_hint: {"center_x": .5}
                                                md_bg_color: 0.9, 0.5, 0.1, 1
                                                opacity: 0
                                                disabled: True
                                                size_hint_y: None
                                                height: "0dp"
                                                on_release: app.claim_daily_bonus()

                                        # Biểu đồ dọc trên Mobile
                                        BoxLayout:
                                            orientation: "vertical"
                                            size_hint_y: None
                                            height: "400dp"
                                            spacing: "10dp"
                                            MDCard:
                                                radius: [15]
                                                padding: "10dp"
                                                md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                                elevation: 0
                                                orientation: "vertical"
                                                BoxLayout:
                                                    size_hint_y: None
                                                    height: "30dp"
                                                    MDLabel:
                                                        text: "Carbon (kg CO2)"
                                                        font_style: "Caption"
                                                        bold: True
                                                    MDLabel:
                                                        text: "↓ 18%"
                                                        font_style: "Caption"
                                                        halign: "right"
                                                        theme_text_color: "Custom"
                                                        text_color: 0.2, 0.6, 0.2, 1
                                                BoxLayout:
                                                    orientation: "horizontal"
                                                    BoxLayout:
                                                        orientation: "vertical"
                                                        size_hint_x: None
                                                        width: "20dp"
                                                        MDLabel:
                                                            text: "8"
                                                            font_style: "Caption"
                                                            font_size: "8sp"
                                                        MDLabel:
                                                            text: "4"
                                                            font_style: "Caption"
                                                            font_size: "8sp"
                                                        MDLabel:
                                                            text: "0"
                                                            font_style: "Caption"
                                                            font_size: "8sp"
                                                    BoxLayout:
                                                        orientation: "vertical"
                                                        LineChart:
                                                            data: [4.2, 3.8, 5.1, 3.2, 2.9, 2.1, 3.4]
                                                            max_val: 8

                                            MDCard:
                                                radius: [15]
                                                padding: "10dp"
                                                md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                                elevation: 0
                                                orientation: "vertical"
                                                BoxLayout:
                                                    size_hint_y: None
                                                    height: "30dp"
                                                    MDLabel:
                                                        text: "Weekly Score"
                                                        font_style: "Caption"
                                                        bold: True
                                                BoxLayout:
                                                    orientation: "horizontal"
                                                    BoxLayout:
                                                        orientation: "vertical"
                                                        size_hint_x: None
                                                        width: "20dp"
                                                        MDLabel:
                                                            text: "100"
                                                            font_style: "Caption"
                                                            font_size: "8sp"
                                                        MDLabel:
                                                            text: "50"
                                                            font_style: "Caption"
                                                            font_size: "8sp"
                                                        MDLabel:
                                                            text: "0"
                                                            font_style: "Caption"
                                                            font_size: "8sp"
                                                    BoxLayout:
                                                        orientation: "vertical"
                                                        BarChart:
                                                            data: [60, 70, 68, 85]
                                                            max_val: 100

                            # === 2. GHI NHẬN HÌNH ẢNH / UPLOAD ===
                            Screen:
                                name: "tab_ghi_nhan"
                                BoxLayout:
                                    orientation: "vertical"
                                    padding: "10dp"
                                    spacing: "10dp"
                                    MDCard:
                                        size_hint_y: 0.85
                                        radius: [15]
                                        padding: "10dp"
                                        spacing: "10dp"
                                        elevation: 1
                                        orientation: "vertical"
                                        md_bg_color: app.theme_cls.bg_light
                                        MDLabel:
                                            id: task_title_label
                                            text: ""
                                            halign: "center"
                                            font_style: "Subtitle2"
                                            bold: True
                                            theme_text_color: "Custom"
                                            text_color: 0.2, 0.5, 0.2, 1
                                            size_hint_y: None
                                            height: "0dp"
                                            opacity: 0
                                        MDLabel:
                                            id: status_label
                                            text: "Vui lòng chọn hoặc chụp ảnh"
                                            halign: "center"
                                            font_style: "Caption"
                                            bold: True
                                            theme_text_color: "Primary"
                                            size_hint_y: None
                                            height: "40dp"
                                        SafeAnchorLayout:
                                            anchor_x: "center"
                                            anchor_y: "center"
                                            Image:
                                                id: preview_image
                                                source: ""
                                                size_hint: 0.9, 0.9

                                        BoxLayout:
                                            size_hint_y: None
                                            height: "40dp"
                                            spacing: "10dp"
                                            MDFillRoundFlatButton:
                                                id: btn_confirm
                                                text: "XÁC NHẬN"
                                                font_size: "12sp"
                                                size_hint_x: 0.7
                                                md_bg_color: 0.1, 0.45, 0.8, 1
                                                disabled: True
                                                on_release: app.confirm_upload()
                                            MDRaisedButton:
                                                id: delete_image_btn
                                                text: "XÓA"
                                                font_size: "12sp"
                                                size_hint_x: 0.3
                                                md_bg_color: 0.8, 0.2, 0.2, 1
                                                opacity: 0
                                                disabled: True
                                                on_release: app.clear_current_image()
                                    BoxLayout:
                                        size_hint_y: None
                                        height: "50dp"
                                        spacing: "10dp"
                                        MDFillRoundFlatIconButton:
                                            icon: "camera"
                                            text: "CHỤP ẢNH"
                                            font_size: "12sp"
                                            size_hint_x: 0.5
                                            md_bg_color: 0.18, 0.49, 0.2, 1
                                            on_release: app.open_camera_popup()
                                        MDFillRoundFlatIconButton:
                                            icon: "upload"
                                            text: "TẢI LÊN"
                                            font_size: "12sp"
                                            size_hint_x: 0.5
                                            md_bg_color: 0.25, 0.35, 0.5, 1
                                            on_release: app.trigger_upload_macos()

                            # === 3. GAMIFICATION CHÍNH ===
                            Screen:
                                name: "tab_gamification"
                                ScrollView:
                                    BoxLayout:
                                        orientation: "vertical"
                                        spacing: "15dp"
                                        padding: "10dp"
                                        size_hint_y: None
                                        height: self.minimum_height

                                        MDCard:
                                            radius: [15]
                                            size_hint_y: None
                                            height: "90dp"
                                            padding: "10dp"
                                            md_bg_color: (0.85, 0.9, 0.85, 1) if app.theme_cls.theme_style == "Light" else (0.18, 0.25, 0.18, 1)
                                            elevation: 0
                                            orientation: "horizontal"
                                            spacing: "10dp"
                                            MDIcon:
                                                icon: "lightning-bolt"
                                                theme_text_color: "Custom"
                                                text_color: 1, 1, 1, 1
                                                size_hint_x: None
                                                width: "30dp"
                                                canvas.before:
                                                    Color:
                                                        rgba: 0.5, 0.7, 0.5, 1
                                                    Ellipse:
                                                        pos: self.center_x - 15, self.center_y - 15
                                                        size: 30, 30
                                            BoxLayout:
                                                orientation: "vertical"
                                                spacing: "2dp"
                                                MDLabel:
                                                    id: gami_level_title
                                                    text: "Level 12"
                                                    bold: True
                                                    font_style: "Subtitle2"
                                                MDLabel:
                                                    id: gami_xp_text
                                                    text: "2840/3000 XP"
                                                    font_style: "Caption"
                                                    font_size: "10sp"
                                                    theme_text_color: "Hint"
                                                MDProgressBar:
                                                    id: gami_main_progress
                                                    value: 80
                                                    color: 0.4, 0.6, 0.4, 1
                                            BoxLayout:
                                                orientation: "vertical"
                                                size_hint_x: None
                                                width: "60dp"
                                                MDIcon:
                                                    icon: "fire"
                                                    halign: "center"
                                                    theme_text_color: "Custom"
                                                    text_color: 0.9, 0.4, 0.1, 1
                                                MDLabel:
                                                    id: gami_streak_text
                                                    text: "12 day"
                                                    halign: "center"
                                                    bold: True
                                                    font_style: "Caption"
                                                    font_size: "10sp"

                                        # -- ROADMAP HIỂN THỊ TRỰC TIẾP --
                                        MDCard:
                                            orientation: "vertical"
                                            padding: "15dp"
                                            spacing: "5dp"
                                            radius: [15]
                                            elevation: 0
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            size_hint_y: None
                                            height: "170dp"
                                            BoxLayout:
                                                orientation: "horizontal"
                                                size_hint_y: None
                                                height: "35dp"
                                                BoxLayout:
                                                    orientation: "vertical"
                                                    spacing: "2dp"
                                                    MDLabel:
                                                        text: "Your Eco Journey"
                                                        bold: True
                                                        font_style: "Subtitle1"
                                                    MDLabel:
                                                        text: "LEVEL ROADMAP"
                                                        font_style: "Caption"
                                                        theme_text_color: "Hint"
                                                        font_size: "9sp"
                                                AnchorLayout:
                                                    anchor_x: "right"
                                                    anchor_y: "center"
                                                    MDCard:
                                                        size_hint: None, None
                                                        size: "105dp", "26dp"
                                                        radius: [13]
                                                        md_bg_color: (0.82, 0.88, 0.82, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.3, 0.2, 1)
                                                        padding: ["5dp", "2dp", "5dp", "2dp"]
                                                        elevation: 0
                                                        MDLabel:
                                                            text: f"{app.user_points} XP all-time"
                                                            halign: "center"
                                                            valign: "center"
                                                            bold: True
                                                            font_style: "Caption"
                                                            font_size: "10sp"
                                                            theme_text_color: "Custom"
                                                            text_color: (0.18, 0.49, 0.2, 1) if app.theme_cls.theme_style == "Light" else (0.8, 0.9, 0.8, 1)
                                            ScrollView:
                                                do_scroll_y: False
                                                do_scroll_x: True
                                                size_hint_y: None
                                                height: "100dp"
                                                BoxLayout:
                                                    id: roadmap_timeline
                                                    orientation: "horizontal"
                                                    size_hint_x: None
                                                    width: self.minimum_width
                                                    spacing: "2dp"
                                                    padding: ["2dp", "5dp", "2dp", "2dp"]

                                        MDLabel:
                                            text: "Monthly Challenges"
                                            bold: True
                                            font_style: "Subtitle2"
                                            size_hint_y: None
                                            height: "20dp"
                                        ActiveChallenge:
                                            c_title: "Plastic-Free July"
                                            c_sub: "Avoid single-use plastics"
                                            c_icon: "recycle"
                                            c_prog_text: "21/30 days"
                                            c_prog_val: 68
                                            c_tag: "500 XP"
                                        ActiveChallenge:
                                            c_title: "Cycle to Work"
                                            c_sub: "Commute by bike 15 times"
                                            c_icon: "bike"
                                            c_prog_text: "6/15 days"
                                            c_prog_val: 40
                                            c_tag: "300 XP"

                                        MDCard:
                                            radius: [15]
                                            size_hint_y: None
                                            height: "500dp"
                                            padding: "15dp"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0
                                            orientation: "vertical"
                                            spacing: "10dp"

                                            BoxLayout:
                                                orientation: "horizontal"
                                                size_hint_y: None
                                                height: "20dp"

                                                MDLabel:
                                                    text: "🏆 Trophy Case"
                                                    bold: True
                                                    font_style: "Subtitle2"

                                                MDLabel:
                                                    id: trophy_count_label
                                                    text: "3 of 10 trophies unlocked"
                                                    halign: "right"
                                                    font_style: "Caption"
                                                    theme_text_color: "Hint"

                                            GridLayout:
                                                id: trophy_grid
                                                cols: 2
                                                spacing: "10dp"
                                                row_default_height: "90dp"
                                                row_force_default: True

                            # === 4. SOCIAL & FEED ===
                            Screen:
                                name: "tab_social"
                                ScrollView:
                                    BoxLayout:
                                        orientation: "vertical"
                                        spacing: "15dp"
                                        padding: "10dp"
                                        size_hint_y: None
                                        height: self.minimum_height

                                        MDCard:
                                            size_hint_y: None
                                            height: "200dp"
                                            radius: [15]
                                            padding: "15dp"
                                            orientation: "vertical"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0
                                            spacing: "10dp"
                                            MDLabel:
                                                text: "Bạn Bè"
                                                bold: True
                                                font_style: "Subtitle2"
                                                size_hint_y: None
                                                height: "20dp"
                                            ScrollView:
                                                MDList:
                                                    id: friends_list
                                                    OneLineAvatarIconListItem:
                                                        text: "Aria Chen"
                                                        IconLeftWidget:
                                                            icon: "account-circle"
                                                            theme_text_color: "Custom"
                                                            text_color: 0.4, 0.6, 0.4, 1
                                                    OneLineAvatarIconListItem:
                                                        text: "Bảo Minh"
                                                        IconLeftWidget:
                                                            icon: "account-circle"
                                                            theme_text_color: "Custom"
                                                            text_color: 0.4, 0.6, 0.4, 1
                                                    OneLineAvatarIconListItem:
                                                        text: "Hải Đăng"
                                                        IconLeftWidget:
                                                            icon: "account-circle"
                                                            theme_text_color: "Custom"
                                                            text_color: 0.4, 0.6, 0.4, 1

                                        MDCard:
                                            size_hint_y: None
                                            height: "400dp"
                                            radius: [15]
                                            padding: "15dp"
                                            orientation: "vertical"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0
                                            spacing: "10dp"
                                            MDLabel:
                                                text: "Eco Feed"
                                                bold: True
                                                font_style: "Subtitle2"
                                                size_hint_y: None
                                                height: "20dp"
                                            ScrollView:
                                                BoxLayout:
                                                    orientation: "vertical"
                                                    spacing: "10dp"
                                                    size_hint_y: None
                                                    height: self.minimum_height

                                                    SocialFeedItem:
                                                        user_name: "Bảo Minh"
                                                        action_text: "đạp xe 5km đi làm."
                                                        like_count: "12"
                                                    SocialFeedItem:
                                                        user_name: "Hải Đăng"
                                                        action_text: "phân loại 2kg rác."
                                                        like_count: "5"
                                                    SocialFeedItem:
                                                        user_name: "Ngọc Anh"
                                                        action_text: "trồng 3 cây xanh."
                                                        like_count: "15"
                                                    SocialFeedItem:
                                                        user_name: "Hoàng Tú"
                                                        action_text: "tái chế vỏ chai."
                                                        like_count: "8"

                            # === 5. TEAM & GROUPS ===
                            Screen:
                                name: "tab_groups"
                                ScrollView:
                                    BoxLayout:
                                        orientation: "vertical"
                                        spacing: "15dp"
                                        padding: "10dp"
                                        size_hint_y: None
                                        height: self.minimum_height

                                        MDCard:
                                            radius: [15]
                                            size_hint_y: None
                                            height: "400dp"
                                            padding: "15dp"
                                            spacing: "10dp"
                                            orientation: "vertical"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0

                                            MDLabel:
                                                text: "Team Leaderboard"
                                                bold: True
                                                font_style: "Subtitle2"
                                                size_hint_y: None
                                                height: "30dp"

                                            TeamLeaderboardItem:
                                                rank_text: "1"
                                                user_name: "Marcus T."
                                                user_xp: "4,280"
                                                progress_val: 100

                                            TeamLeaderboardItem:
                                                rank_text: "2"
                                                user_name: "Yuki S."
                                                user_xp: "3,940"
                                                progress_val: 92

                                            TeamLeaderboardItem:
                                                rank_text: "3"
                                                user_name: "Aria"
                                                user_xp: "3,680"
                                                progress_val: 86
                                                is_me: True

                                            TeamLeaderboardItem:
                                                rank_text: "4"
                                                user_name: "Camille R."
                                                user_xp: "3,210"
                                                progress_val: 75

                                            TeamLeaderboardItem:
                                                rank_text: "5"
                                                user_name: "Dev P."
                                                user_xp: "2,990"
                                                progress_val: 69

                                        MDCard:
                                            radius: [15]
                                            size_hint_y: None
                                            height: "170dp"
                                            padding: "15dp"
                                            spacing: "10dp"
                                            orientation: "vertical"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0

                                            BoxLayout:
                                                orientation: "horizontal"
                                                size_hint_y: None
                                                height: "20dp"
                                                MDLabel:
                                                    text: "Team Target"
                                                    bold: True
                                                    font_style: "Subtitle2"

                                            BoxLayout:
                                                orientation: "vertical"
                                                size_hint_y: None
                                                height: "60dp"
                                                canvas.before:
                                                    Color:
                                                        rgba: (0.85, 0.89, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
                                                    RoundedRectangle:
                                                        pos: self.pos
                                                        size: self.size
                                                        radius: [10]
                                                padding: "5dp"
                                                MDLabel:
                                                    text: "🌍 Mục tiêu 20,000 Điểm"
                                                    bold: True
                                                    font_style: "Caption"
                                                MDLabel:
                                                    text: "Cùng nhau đạt 20k XP tổng để nhận thưởng."
                                                    font_style: "Caption"
                                                    font_size: "10sp"
                                                    theme_text_color: "Hint"

                                            BoxLayout:
                                                orientation: "vertical"
                                                size_hint_y: None
                                                height: "30dp"
                                                BoxLayout:
                                                    orientation: "horizontal"
                                                    MDLabel:
                                                        text: "18,100 / 20,000"
                                                        font_style: "Caption"
                                                        font_size: "10sp"
                                                        theme_text_color: "Hint"
                                                    MDLabel:
                                                        text: "90%"
                                                        font_style: "Caption"
                                                        font_size: "10sp"
                                                        bold: True
                                                        halign: "right"
                                                        theme_text_color: "Hint"
                                                CustomProgressBar:
                                                    value: 90

                            # === 6. PROFILE & SETTINGS ===
                            Screen:
                                name: "tab_stats"
                                ScrollView:
                                    BoxLayout:
                                        orientation: "vertical"
                                        spacing: "15dp"
                                        padding: "10dp"
                                        size_hint_y: None
                                        height: self.minimum_height

                                        MDCard:
                                            radius: [15]
                                            size_hint_y: None
                                            height: "140dp"
                                            padding: "15dp"
                                            orientation: "vertical"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0

                                            BoxLayout:
                                                orientation: "horizontal"
                                                spacing: "10dp"

                                                MDIcon:
                                                    icon: "account-circle"
                                                    font_size: "60sp"
                                                    size_hint_x: None
                                                    width: "60dp"
                                                    theme_text_color: "Custom"
                                                    text_color: 0.4, 0.5, 0.4, 1

                                                BoxLayout:
                                                    orientation: "vertical"
                                                    spacing: "2dp"
                                                    MDLabel:
                                                        id: profile_name_label
                                                        text: "Aria Chen"
                                                        font_style: "Subtitle1"
                                                        bold: True
                                                    MDLabel:
                                                        id: profile_location_label
                                                        text: "San Francisco, CA"
                                                        font_style: "Caption"
                                                        font_size: "10sp"
                                                        theme_text_color: "Hint"
                                                    BoxLayout:
                                                        orientation: "horizontal"
                                                        spacing: "5dp"
                                                        MDLabel:
                                                            text: "🌿 Lv 12"
                                                            font_style: "Caption"
                                                            font_size: "10sp"
                                                            bold: True
                                                            theme_text_color: "Custom"
                                                            text_color: 0.3, 0.6, 0.3, 1
                                                        MDLabel:
                                                            text: "🔥 12 day"
                                                            font_style: "Caption"
                                                            font_size: "10sp"
                                                            bold: True
                                                            theme_text_color: "Custom"
                                                            text_color: 0.9, 0.5, 0.1, 1
                                                MDIconButton:
                                                    icon: "pencil"
                                                    on_release: app.open_edit_profile_popup()

                                        GridLayout:
                                            cols: 2
                                            spacing: "10dp"
                                            size_hint_y: None
                                            height: "220dp"
                                            StatCard:
                                                icon: "leaf"
                                                value: "284"
                                                desc: "Total Habits"
                                            StatCard:
                                                icon: "weather-windy"
                                                value: "82 kg"
                                                desc: "CO2 Offset"
                                            StatCard:
                                                icon: "water-outline"
                                                value: "3.2k L"
                                                desc: "Water Saved"
                                            StatCard:
                                                icon: "lightning-bolt"
                                                value: "2,840"
                                                desc: "XP Earned"

                                        MDCard:
                                            radius: [15]
                                            padding: "15dp"
                                            size_hint_y: None
                                            height: "250dp"
                                            orientation: "vertical"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0
                                            MDLabel:
                                                text: "Badges"
                                                bold: True
                                                font_style: "Subtitle2"
                                                size_hint_y: None
                                                height: "20dp"
                                            GridLayout:
                                                cols: 3
                                                spacing: "10dp"
                                                BadgeItem:
                                                    icon: "seed"
                                                    title: "Seedling"
                                                    unlocked: True
                                                BadgeItem:
                                                    icon: "water"
                                                    title: "Water"
                                                    unlocked: True
                                                BadgeItem:
                                                    icon: "leaf"
                                                    title: "Carbon"
                                                    unlocked: True
                                                BadgeItem:
                                                    icon: "fire"
                                                    title: "Streak"
                                                    unlocked: False
                                                BadgeItem:
                                                    icon: "bike"
                                                    title: "Commuter"
                                                    unlocked: False
                                                BadgeItem:
                                                    icon: "recycle"
                                                    title: "Zero Waste"
                                                    unlocked: False

                                        MDCard:
                                            radius: [15]
                                            padding: "15dp"
                                            size_hint_y: None
                                            height: "220dp"
                                            orientation: "vertical"
                                            spacing: "5dp"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0
                                            MDLabel:
                                                text: "Goals"
                                                bold: True
                                                font_style: "Subtitle2"
                                                size_hint_y: None
                                                height: "20dp"
                                            GoalItem:
                                                title: "Reduce carbon to 3 kg"
                                                progress_text: "3.4/3 kg"
                                                value: 85
                                            GoalItem:
                                                title: "Log 300 habits"
                                                progress_text: "284/300"
                                                value: 94
                                            GoalItem:
                                                title: "Reach Eco Score 90+"
                                                progress_text: "84/90"
                                                value: 93
                                            MDFillRoundFlatButton:
                                                text: "Update Goals"
                                                pos_hint: {"center_x": 0.5}
                                                size_hint_x: 0.8
                                                text_color: 1, 1, 1, 1
                                                md_bg_color: 0.4, 0.55, 0.4, 1
                                                on_release: app.open_update_goals_popup()

                                        MDCard:
                                            radius: [15]
                                            padding: "15dp"
                                            orientation: "vertical"
                                            size_hint_y: None
                                            height: "240dp"
                                            spacing: "10dp"
                                            md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                            elevation: 0
                                            BoxLayout:
                                                orientation: "horizontal"
                                                size_hint_y: None
                                                height: "30dp"
                                                MDLabel:
                                                    text: "Preferences"
                                                    bold: True
                                                    font_style: "Subtitle2"
                                                MDRoundFlatIconButton:
                                                    icon: "theme-light-dark"
                                                    text: "Sáng/Tối"
                                                    font_size: "10sp"
                                                    md_bg_color: 0, 0, 0, 0
                                                    line_color: 0.7, 0.7, 0.7, 1
                                                    size_hint_y: None
                                                    height: "30dp"
                                                    on_release: app.toggle_theme()
                                            PrefItem:
                                                icon: "alarm"
                                                title: "Reminder"
                                                value: "8:00 AM"
                                            PrefItem:
                                                icon: "ruler"
                                                title: "Units"
                                                value: "Metric"
                                            PrefItem:
                                                icon: "lock"
                                                title: "Privacy"
                                                value: "Friends only"

            # -- NAVIGATION DRAWER (SIDEBAR ẨN) --
            MDNavigationDrawer:
                id: nav_drawer
                radius: (0, 16, 16, 0)
                md_bg_color: (0.91, 0.93, 0.90, 1) if app.theme_cls.theme_style == "Light" else (0.12, 0.12, 0.12, 1)

                ScrollView:
                    BoxLayout:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        size_hint_y: None
                        height: self.minimum_height

                        BoxLayout:
                            orientation: "horizontal"
                            size_hint_y: None
                            height: "50dp"
                            spacing: "12dp"
                            MDIconButton:
                                icon: "leaf"
                                md_bg_color: 0.6, 0.7, 0.6, 1
                                theme_text_color: "Custom"
                                text_color: 1, 1, 1, 1
                                user_font_size: "20sp"
                            BoxLayout:
                                orientation: "vertical"
                                MDLabel:
                                    text: "Eco Tracker"
                                    bold: True
                                    font_style: "Subtitle2"
                                    theme_text_color: "Primary"
                                MDLabel:
                                    text: "Impact Monitor"
                                    font_style: "Caption"
                                    font_size: "10sp"
                                    theme_text_color: "Secondary"

                        Widget:
                            size_hint_y: None
                            height: "10dp"

                        MDCard:
                            size_hint_y: None
                            height: "80dp"
                            radius: [15]
                            padding: "12dp"
                            md_bg_color: (0.88, 0.91, 0.86, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.15, 0.1, 1)
                            elevation: 0
                            orientation: "vertical"
                            spacing: "5dp"
                            BoxLayout:
                                orientation: "horizontal"
                                MDIcon:
                                    icon: "fire"
                                    theme_text_color: "Custom"
                                    text_color: 0.9, 0.4, 0.1, 1
                                    size_hint_x: None
                                    width: "25dp"
                                MDLabel:
                                    id: sidebar_streak_label
                                    text: "12-day streak"
                                    bold: True
                                    font_style: "Caption"
                                    theme_text_color: "Primary"
                            MDProgressBar:
                                value: 72
                                color: 0.4, 0.6, 0.4, 1
                            MDLabel:
                                text: "72% to milestone"
                                font_style: "Caption"
                                theme_text_color: "Hint"
                                font_size: "10sp"

                        Widget:
                            size_hint_y: None
                            height: "15dp"

                        SidebarButton:
                            id: nav_dashboard
                            icon: "view-dashboard"
                            text: "Dashboard"
                            md_bg_color: [0.7, 0.78, 0.7, 0.6]
                            on_release: app.switch_tab("tab_dashboard", self, "Dashboard")
                        SidebarButton:
                            id: nav_gamification
                            icon: "trophy-outline"
                            text: "Gamification"
                            on_release: app.switch_tab("tab_gamification", self, "Challenges")
                        SidebarButton:
                            id: nav_social
                            icon: "account-group-outline"
                            text: "Social & Feed"
                            on_release: app.switch_tab("tab_social", self, "Community")
                        SidebarButton:
                            id: nav_groups
                            icon: "account-multiple"
                            text: "Team & Groups"
                            on_release: app.switch_tab("tab_groups", self, "Teams")
                        SidebarButton:
                            id: nav_stats
                            icon: "account-details"
                            text: "Profile"
                            on_release: app.switch_tab("tab_stats", self, "Profile")

                        Widget:
                            size_hint_y: None
                            height: "50dp"

                        MDCard:
                            size_hint_y: None
                            height: "60dp"
                            radius: [15]
                            padding: "10dp"
                            md_bg_color: (0.88, 0.91, 0.86, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.15, 0.1, 1)
                            elevation: 0
                            orientation: "vertical"
                            BoxLayout:
                                orientation: "horizontal"
                                MDIcon:
                                    icon: "lightning-bolt"
                                    theme_text_color: "Custom"
                                    text_color: 0.4, 0.6, 0.4, 1
                                    size_hint_x: None
                                    width: "20dp"
                                MDLabel:
                                    id: sidebar_points_label
                                    text: "2,840 XP"
                                    bold: True
                                    font_style: "Caption"
                                    theme_text_color: "Primary"
                                MDLabel:
                                    id: sidebar_level_label
                                    text: "Lv 12"
                                    halign: "right"
                                    font_style: "Caption"
                                    theme_text_color: "Hint"
                            MDProgressBar:
                                id: sidebar_level_progress
                                value: 80
                                color: 0.4, 0.6, 0.4, 1

                        BoxLayout:
                            orientation: "horizontal"
                            size_hint_y: None
                            height: "50dp"
                            spacing: "10dp"
                            MDIconButton:
                                icon: "logout"
                                md_bg_color: 0.8, 0.3, 0.3, 1
                                theme_text_color: "Custom"
                                text_color: 1, 1, 1, 1
                                on_release: app.process_logout()
                            BoxLayout:
                                orientation: "vertical"
                                MDLabel:
                                    id: username_display
                                    text: "Aria Chen"
                                    bold: True
                                    font_style: "Caption"
                                    theme_text_color: "Primary"
                                MDLabel:
                                    text: "Eco Enthusiast"
                                    font_style: "Caption"
                                    theme_text_color: "Secondary"
                                    font_size: "10sp"
'''


class EcoTrackerApp(MDApp):

    # -- THÔNG TIN AWS --
    SERVER_URL = "http://13.212.xx.xx:8000" 

    current_photo_path = ""
    
    # -- THUỘC TÍNH ĐỘNG --
    user_points = NumericProperty(2840)
    user_streak = NumericProperty(12)
    bonus_claimed = BooleanProperty(False) # Track nút nhận 200XP

    uploaded_hashes = []
    current_hash = ""

    current_eco_score = 84
    current_eco_today = 8

    # --- Daily tasks state ---
    daily_tasks = []          # list of dicts: {title, desc, icon, completed}
    current_task_index = None  # index of task đang được upload, None = upload thường

    # ĐỊNH NGHĨA CÁC MỐC ĐIỂM VÀ TÊN HUY HIỆU (Đã đồng bộ)
    trophy_thresholds = [500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000]
    trophy_icons = ["seed", "water", "leaf", "fire", "bike", "recycle", "earth", "star", "tree", "crown"]
    trophy_names = ["Seedling", "Water Guardian", "Carbon Cutter", "Streak Master", "Green Commuter", "Zero Waste", "Earth Hero", "Star Eco", "Tree Planter", "Eco Crown"]

    trophy_descriptions = [
        "Đạt tổng cộng 500 XP.",
        "Tiết kiệm nước, đạt 1,000 XP.",
        "Giảm phát thải, đạt 1,500 XP.",
        "Đạt 2,000 XP tổng.",
        "Đạt 2,500 XP tổng.",
        "Phân loại rác tốt, đạt 3,000 XP.",
        "Cống hiến vì môi trường, đạt 4,000 XP.",
        "Gương sáng 5,000 XP.",
        "Góp phần phủ xanh, đạt 7,500 XP.",
        "Huy hiệu tối thượng 10,000 XP."
    ]

    def build(self):
        self.theme_cls.primary_palette = "Green"
        self.store = JsonStore('eco_settings.json')
        if self.store.exists('theme'):
            self.theme_cls.theme_style = self.store.get('theme')['style']
        else:
            self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)

    def on_start(self):
        self.update_trophy_case()
        self.update_roadmap_ui()
        self.check_eco_path_milestones()
        self.generate_daily_tasks()

    # =========================================================
    # HÀM VẼ TIẾN TRÌNH LEVEL ROADMAP DỌC/NGANG (Tự động co giãn)
    # =========================================================
    def update_roadmap_ui(self):
        try:
            timeline = self.root.ids.roadmap_timeline
        except Exception:
            return
            
        timeline.clear_widgets()
        
        # Tạo thêm 1 mốc khởi đầu "Beginner" tương ứng với 0 XP (luôn mở khóa)
        milestones_thresholds = [0] + self.trophy_thresholds
        milestones_names = ["Beginner"] + self.trophy_names
        milestones_icons = ["account-outline"] + self.trophy_icons
        
        num_milestones = len(milestones_thresholds)
        
        for i in range(num_milestones):
            name = milestones_names[i]
            threshold = milestones_thresholds[i]
            icon = milestones_icons[i]
            
            # Kiểm tra xem user hiện tại đã mở khóa mốc này chưa
            is_unlocked = self.user_points >= threshold
            
            # Thêm Node mốc tiến trình
            node = Builder.load_string(f'''
RoadmapNode:
    node_name: "{name}"
    node_points: "{threshold}"
    node_icon: "{icon}"
    is_unlocked: {is_unlocked}
''')
            timeline.add_widget(node)
            
            # Nếu chưa phải mốc cuối cùng, thêm đường nối giữa 2 Node
            if i < num_milestones - 1:
                curr_thresh = milestones_thresholds[i]
                next_thresh = milestones_thresholds[i + 1]
                
                # Tính toán tỷ lệ phần trăm lấp đầy thanh nối theo điểm số thực tế
                if self.user_points >= next_thresh:
                    progress_val = 1.0
                elif self.user_points < curr_thresh:
                    progress_val = 0.0
                else:
                    # Tính tỷ lệ nằm giữa 2 mốc điểm
                    progress_val = (self.user_points - curr_thresh) / (next_thresh - curr_thresh)
                
                connector = Builder.load_string(f'''
TimelineConnector:
    progress_val: {progress_val}
''')
                timeline.add_widget(connector)

    # =========================================================
    # DAILY TASKS & BONUS
    # =========================================================
    def generate_daily_tasks(self):
        """Lấy random 3 task từ danh sách tổng cho ngày hôm nay."""
        self.bonus_claimed = False # Reset trạng thái nhận thưởng khi có task mới
        picked = random.sample(DAILY_TASKS_POOL, k=min(3, len(DAILY_TASKS_POOL)))
        self.daily_tasks = []
        for t in picked:
            self.daily_tasks.append({
                "title": t["title"],
                "desc": t["desc"],
                "icon": t["icon"],
                "completed": False,
            })
        self.update_daily_tasks_ui()

    def update_daily_tasks_ui(self):
        try:
            box = self.root.ids.daily_tasks_box
        except Exception:
            return
            
        box.clear_widgets()
        done_count = 0
        
        for idx, task in enumerate(self.daily_tasks):
            if task["completed"]:
                done_count += 1
            
            # Tạo widget cho từng nhiệm vụ (Khóa nút nếu đã completed)
            item = Builder.load_string(f'''
DailyTaskItem:
    task_index: {idx}
    icon: "{task['icon']}"
    title: "{task['title']}"
    desc: "{task['desc']}"
    completed: {task['completed']}
    on_release: app.open_task_upload({idx}) if not {task['completed']} else None
''')
            box.add_widget(item)
            
        # XỬ LÝ THANH TIẾN ĐỘ VÀ NÚT NHẬN THƯỞNG 200XP
        try:
            total_tasks = len(self.daily_tasks)
            self.root.ids.daily_tasks_progress_label.text = f"{done_count}/{total_tasks} hoàn thành"
            
            btn = self.root.ids.claim_bonus_btn
            if done_count == total_tasks and not self.bonus_claimed:
                # Đủ 3/3 và chưa nhận -> HIỆN NÚT CAM
                btn.opacity = 1
                btn.disabled = False
                btn.height = "40dp"
                btn.text = "🎉 NHẬN 200 XP THƯỞNG"
                btn.md_bg_color = (0.9, 0.5, 0.1, 1)
            elif done_count == total_tasks and self.bonus_claimed:
                # Đủ 3/3 và đã nhận -> ĐỔI MÀU XANH, KHÓA NÚT
                btn.opacity = 1
                btn.disabled = True
                btn.height = "40dp"
                btn.text = "ĐÃ NHẬN THƯỞNG"
                btn.md_bg_color = (0.4, 0.6, 0.4, 1)
            else:
                # Chưa đủ 3/3 -> ẨN NÚT
                btn.opacity = 0
                btn.disabled = True
                btn.height = "0dp"
                
        except Exception:
            pass

    def claim_daily_bonus(self):
        """Hàm xử lý khi người dùng bấm nút nhận 200 XP thưởng."""
        if not self.bonus_claimed:
            # 1. Cộng điểm
            self.user_points += 200
            self.bonus_claimed = True
            
            # 2. Cập nhật giao diện
            self.update_daily_tasks_ui()
            self.update_trophy_case()
            self.update_roadmap_ui()
            self.check_eco_path_milestones()
            
            # 3. (Tùy chọn) Gửi số điểm mới lên AWS để lưu
            try:
                payload = {
                    "username": self.root.ids.login_user.text,
                    "points": self.user_points
                }
                # requests.post(f"{self.SERVER_URL}/update_points", json=payload, timeout=5)
                print("Đã cộng 200XP thưởng vào tổng điểm!")
            except:
                pass

    def open_task_upload(self, task_index):
        if task_index is None or task_index >= len(self.daily_tasks):
            return
        task = self.daily_tasks[task_index]
        if task["completed"]:
            return

        self.current_task_index = task_index
        self.clear_current_image()

        try:
            self.root.ids.task_title_label.text = f"Nhiệm vụ: {task['title']}"
            self.root.ids.task_title_label.opacity = 1
            self.root.ids.task_title_label.height = "30dp"
            self.root.ids.status_label.text = "Chụp/tải ảnh để hoàn thành nhiệm vụ này"
        except Exception:
            pass

        self.switch_tab("tab_ghi_nhan", None, "Upload Photo")

    # =========================================================
    def update_trophy_case(self):
        self.root.ids.trophy_grid.clear_widgets()
        unlocked_count = 0
        for i in range(10):
            is_unlocked = self.user_points >= self.trophy_thresholds[i]
            if is_unlocked:
                unlocked_count += 1
            item = Builder.load_string(f'''
TrophyItem:
    icon: "{self.trophy_icons[i]}"
    title: "{self.trophy_names[i]}"
    desc: "{self.trophy_descriptions[i]}"
    current_p: {self.user_points}
    max_p: {self.trophy_thresholds[i]}
    unlocked: {is_unlocked}
''')
            self.root.ids.trophy_grid.add_widget(item)
        self.root.ids.trophy_count_label.text = f"{unlocked_count} of 10 trophies unlocked"

    def show_trophy_details(self, title, icon, desc, unlocked, current_p, max_p):
        content = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')
        color_rgba = (0.3, 0.7, 0.3, 1) if unlocked else (0.6, 0.6, 0.6, 0.5)
        icon_widget = MDLabel(
            text=f"[font=Icons][size=60]{icon}[/size][/font]",
            markup=True, halign='center', theme_text_color='Custom',
            text_color=color_rgba, size_hint_y=None, height='80dp'
        )
        content.add_widget(icon_widget)
        content.add_widget(MDLabel(text=title, font_style='Subtitle1', bold=True, halign='center', size_hint_y=None, height='30dp'))

        status_text = "[color=#4CAF50]Đã mở khóa[/color]" if unlocked else "[color=#F44336]Chưa mở khóa[/color]"
        content.add_widget(MDLabel(text=status_text, markup=True, halign='center', font_style='Caption', size_hint_y=None, height='20dp'))
        content.add_widget(MDLabel(text=desc, halign='center', font_style="Caption", theme_text_color='Secondary', size_hint_y=None, height='50dp'))

        if not unlocked:
            prog_box = BoxLayout(orientation='vertical', size_hint_y=None, height='50dp')
            prog_label = MDLabel(text=f"{current_p}/{max_p} XP", font_style='Caption', halign='center')
            safe_value = min(100, max(0, (current_p / max_p) * 100))
            prog_bar = MDProgressBar(value=safe_value, color=(0.4, 0.6, 0.4, 1), size_hint_y=None, height='5dp')
            prog_box.add_widget(prog_label)
            prog_box.add_widget(prog_bar)
            content.add_widget(prog_box)
        else:
            content.add_widget(Widget(size_hint_y=None, height='50dp'))

        btn = MDFillRoundFlatButton(text="ĐÓNG", pos_hint={'center_x': 0.5}, md_bg_color=(0.4, 0.6, 0.4, 1))
        content.add_widget(btn)

        self.trophy_popup = Popup(title="Chi tiết", content=content, size_hint=(0.8, 0.6))
        btn.bind(on_release=lambda x: self.trophy_popup.dismiss())
        self.trophy_popup.open()

    def check_eco_path_milestones(self):
        level = (self.user_points // 1000) + 10
        next_level_xp = ((level - 9) * 1000) + 2000
        progress = int((self.user_points / next_level_xp) * 100)
        try:
            self.root.ids.sidebar_level_label.text = f"Lv {level}"
            self.root.ids.sidebar_level_progress.value = progress
            self.root.ids.gami_level_title.text = f"Level {level}"
            self.root.ids.gami_xp_text.text = f"{self.user_points}/{next_level_xp} XP"
            self.root.ids.gami_main_progress.value = progress
            self.root.ids.gami_streak_text.text = f"{self.user_streak} day"
        except Exception:
            pass

    def open_edit_profile_popup(self):
        content = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')
        self.edit_name_input = MDTextField(text=self.root.ids.profile_name_label.text, hint_text="Tên", mode="rectangle")
        current_loc = self.root.ids.profile_location_label.text
        self.edit_loc_input = MDTextField(text=current_loc, hint_text="Thành phố", mode="rectangle")
        content.add_widget(self.edit_name_input)
        content.add_widget(self.edit_loc_input)

        save_btn = MDFillRoundFlatButton(text="LƯU", md_bg_color=(0.4, 0.6, 0.4, 1), pos_hint={'center_x': 0.5}, size_hint_x=1)
        save_btn.bind(on_release=self.save_profile)
        content.add_widget(save_btn)
        self.profile_popup = Popup(title="Chỉnh sửa", content=content, size_hint=(0.8, 0.5))
        self.profile_popup.open()

    def save_profile(self, instance):
        if self.edit_name_input.text.strip() != "":
            self.root.ids.profile_name_label.text = self.edit_name_input.text
            self.root.ids.username_display.text = self.edit_name_input.text
        if self.edit_loc_input.text.strip() != "":
            self.root.ids.profile_location_label.text = self.edit_loc_input.text
        self.profile_popup.dismiss()

    def open_update_goals_popup(self):
        content = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')
        content.add_widget(MDTextField(text="3", hint_text="Carbon (kg/ngày)", mode="rectangle"))
        content.add_widget(MDTextField(text="300", hint_text="Habits", mode="rectangle"))
        content.add_widget(MDTextField(text="90", hint_text="Eco Score", mode="rectangle"))
        save_btn = MDFillRoundFlatButton(text="CẬP NHẬT", md_bg_color=(0.4, 0.6, 0.4, 1), pos_hint={'center_x': 0.5}, size_hint_x=1)
        save_btn.bind(on_release=lambda x: self.goals_popup.dismiss())
        content.add_widget(save_btn)
        self.goals_popup = Popup(title="Mục tiêu", content=content, size_hint=(0.8, 0.6))
        self.goals_popup.open()

    def switch_tab(self, screen_name, btn_instance, title="Dashboard"):
        self.root.ids.sm.current = screen_name
        self.root.ids.top_app_bar.title = title

        nav_buttons = [
            self.root.ids.nav_dashboard,
            self.root.ids.nav_gamification,
            self.root.ids.nav_social,
            self.root.ids.nav_groups,
            self.root.ids.nav_stats
        ]
        for btn in nav_buttons:
            if btn:
                btn.md_bg_color = [0, 0, 0, 0]
        if btn_instance:
            btn_instance.md_bg_color = [0.7, 0.78, 0.7, 0.6]

        if "nav_drawer" in self.root.ids:
            self.root.ids.nav_drawer.set_state("close")

    def add_like(self, btn_instance, card_instance):
        current_likes = int(card_instance.like_count)
        current_likes += 1
        card_instance.like_count = str(current_likes)
        card_instance.ids.like_label.text = f"{current_likes} Thích"
        btn_instance.icon = "heart"
        btn_instance.text_color = (0.9, 0.2, 0.2, 1)
        btn_instance.disabled = True

    def toggle_theme(self):
        current = self.theme_cls.theme_style
        new_style = "Dark" if current == "Light" else "Light"
        self.theme_cls.theme_style = new_style
        self.store.put('theme', style=new_style)

    def process_login(self):
        user = self.root.ids.login_user.text
        if user.strip() != "":
            try:
                response = requests.get(f"{self.SERVER_URL}/get_user/{user}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.user_points = data.get('points', 0)
                    self.user_streak = data.get('streak', 0)
                    
                    cloud_tasks = data.get('daily_tasks', [])
                    if cloud_tasks:
                        self.daily_tasks = cloud_tasks
                    print("Đã đồng bộ dữ liệu từ Cloud thành công!")
                else:
                    self.user_points = 0
                    self.user_streak = 0
                    self.generate_daily_tasks() 

            except Exception as e:
                print(f"Lỗi kết nối AWS: {e}")
                # Giữ nguyên điểm cũ nếu mất mạng

            self.root.ids.username_display.text = user
            self.root.ids.profile_name_label.text = user
            self.root.current = "main_app_screen"
            
            self.switch_tab("tab_dashboard", self.root.ids.nav_dashboard, "Dashboard")
            
            self.update_daily_tasks_ui()
            self.update_trophy_case()
            self.update_roadmap_ui()
            self.check_eco_path_milestones()

    def process_logout(self):
        self.root.current = "login_screen"
        self.clear_current_image()

    def open_camera_popup(self):
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        header_layout = BoxLayout(size_hint_y=None, height="40dp")
        header_layout.add_widget(Widget())
        close_btn = MDIconButton(
            icon="close-circle", theme_text_color="Custom", text_color=(0.8, 0.2, 0.2, 1), on_release=self.close_camera_popup
        )
        header_layout.add_widget(close_btn)
        main_layout.add_widget(header_layout)

        self.cam_widget = Camera(play=True, resolution=(640, 480))
        with self.cam_widget.canvas.before:
            PushMatrix()
            self.cam_rot = Rotate(angle=270, axis=(0, 0, 1))
        with self.cam_widget.canvas.after:
            PopMatrix()
        self.cam_widget.bind(size=self._update_camera_origin, pos=self._update_camera_origin)
        main_layout.add_widget(self.cam_widget)

        capture_btn = MDRaisedButton(text="CHỤP", pos_hint={"center_x": 0.5}, md_bg_color=(0.18, 0.49, 0.2, 1))
        capture_btn.bind(on_release=self.capture_photo)
        main_layout.add_widget(capture_btn)

        self.cam_popup = Popup(title="Camera", content=main_layout, size_hint=(0.9, 0.8), auto_dismiss=False)
        self.cam_popup.open()

    def _update_camera_origin(self, instance, value):
        self.cam_rot.origin = instance.center

    def close_camera_popup(self, instance):
        self.cam_widget.play = False
        self.cam_popup.dismiss()

    def capture_photo(self, instance):
        timestamp = int(time.time())
        output_path = os.path.join(UPLOAD_CACHE_DIR, f"captured_{timestamp}.png")
        self.cam_widget.export_to_png(output_path)
        self.cam_widget.play = False
        self.cam_popup.dismiss()
        try:
            img = cv2.imread(output_path)
            if img is not None:
                fixed_img = cv2.rotate(img, cv2.ROTATE_45_CLOCKWISE)
                cv2.imwrite(output_path, fixed_img)
        except Exception:
            pass
        self.show_image_in_preview(output_path)

    def trigger_upload_macos(self):
        applescript = (
            'tell application "System Events"\n'
            '   activate\n'
            '   set filePath to choose file of type {"public.image"} with prompt "Chọn ảnh:"\n'
            '   POSIX path of filePath\n'
            'end tell'
        )
        try:
            proc = subprocess.run(['osascript', '-e', applescript], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode == 0:
                file_path = proc.stdout.strip()
                if file_path:
                    filename = os.path.basename(file_path)
                    destination = os.path.join(UPLOAD_CACHE_DIR, filename)
                    shutil.copy(file_path, destination)
                    self.show_image_in_preview(destination)
        except Exception:
            self.root.ids.status_label.text = "Lỗi nạp file"

    def show_image_in_preview(self, path):
        try:
            with open(path, "rb") as f:
                img_hash = hashlib.md5(f.read()).hexdigest()
            if img_hash in self.uploaded_hashes:
                self.root.ids.status_label.text = "CẢNH BÁO: Ảnh này đã được dùng!"
                self.root.ids.status_label.theme_text_color = "Custom"
                self.root.ids.status_label.text_color = (0.8, 0.2, 0.2, 1)
                os.remove(path)
                return
            self.current_hash = img_hash
        except Exception:
            pass
        self.current_photo_path = path
        self.root.ids.preview_image.source = path
        self.root.ids.preview_image.reload()

        if self.current_task_index is not None:
            self.root.ids.status_label.text = "Bấm XÁC NHẬN để hoàn thành nhiệm vụ."
        else:
            self.root.ids.status_label.text = "Bấm XÁC NHẬN để lưu lại."
        self.root.ids.status_label.theme_text_color = "Primary"
        self.root.ids.btn_confirm.disabled = False
        self.root.ids.delete_image_btn.opacity = 1
        self.root.ids.delete_image_btn.disabled = False

    def clear_current_image(self):
        if self.current_photo_path and os.path.exists(self.current_photo_path):
            try:
                os.remove(self.current_photo_path)
            except Exception:
                pass
        self.current_photo_path = ""
        self.current_hash = ""
        try:
            self.root.ids.preview_image.source = ""
            self.root.ids.status_label.text = "Vui lòng chọn hoặc chụp ảnh"
            self.root.ids.status_label.theme_text_color = "Primary"
            self.root.ids.btn_confirm.disabled = True
            self.root.ids.delete_image_btn.opacity = 0
            self.root.ids.delete_image_btn.disabled = True
            self.root.ids.btn_confirm.text = "XÁC NHẬN"
            self.root.ids.btn_confirm.md_bg_color = (0.1, 0.45, 0.8, 1)
            self.root.ids.task_title_label.text = ""
            self.root.ids.task_title_label.opacity = 0
            self.root.ids.task_title_label.height = "0dp"
        except Exception:
            pass

    def confirm_upload(self):
        if not self.current_photo_path:
            self.root.ids.status_label.text = "Bạn chưa chụp/chọn ảnh!"
            return

        # 1. CẬP NHẬT GIAO DIỆN LOCAL NGAY LẬP TỨC
        if self.current_task_index is not None:
            self.daily_tasks[self.current_task_index]["completed"] = True
            self.user_points += 100  # Cộng 100 XP cho mỗi nhiệm vụ thường
            
            self.update_daily_tasks_ui()
            self.update_trophy_case()
            self.update_roadmap_ui()
            self.check_eco_path_milestones()

        # 2. ĐÓNG GÓI VÀ GỬI LÊN AWS S3
        username = self.root.ids.login_user.text
        task_id = self.current_task_index 
        API_ENDPOINT = f"{self.SERVER_URL}/upload_task" 

        try:
            with open(self.current_photo_path, "rb") as image_file:
                files = {
                    'file': (os.path.basename(self.current_photo_path), image_file, 'image/png')
                }
                data = {
                    "username": username,
                    "task_id": str(task_id)
                }

                # Set timeout=5s để tránh đơ app nếu mạng lỗi
                response = requests.post(API_ENDPOINT, data=data, files=files, timeout=5)

                if response.status_code == 200:
                    ket_qua = response.json()
                    link_anh_s3 = ket_qua.get("image_url")
                    print(f"Ảnh đã lên S3 thành công: {link_anh_s3}")
                    self.root.ids.status_label.text = "Đã đồng bộ ảnh lên S3 Cloud!"
                else:
                    self.root.ids.status_label.text = f"Đã lưu Local (AWS Lỗi {response.status_code})"

        except Exception as e:
            print(f"Lỗi Call API: {e}")
            self.root.ids.status_label.text = "Đã lưu (Chưa kết nối Cloud)"

        self.root.ids.status_label.theme_text_color = "Custom"
        self.root.ids.status_label.text_color = (0.15, 0.55, 0.15, 1)
        self.root.ids.btn_confirm.disabled = True
        Clock.schedule_once(lambda dt: self.go_to_dashboard(), 2.0)

    def go_to_dashboard(self):
        self.current_task_index = None
        self.switch_tab("tab_dashboard", self.root.ids.nav_dashboard, "Dashboard")
        self.clear_current_image()

if __name__ == "__main__":
    EcoTrackerApp().run()