import os
import subprocess
import time
import shutil
import random
import hashlib
from PIL import Image as PILImage

from kivy.config import Config
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from kivy.factory import Factory

try:
    import cv2
    import numpy as np
    AI_VISION_ENABLED = True
except ImportError:
    AI_VISION_ENABLED = False
    print("Cảnh báo: Thiếu thư viện OpenCV hoặc Numpy.")

# 1. THIẾT LẬP CẤU HÌNH MÀN HÌNH CHUẨN ĐIỆN THOẠI/TABLET NGANG
Config.set('graphics', 'width', '1050')
Config.set('graphics', 'height', '700')
Config.set('graphics', 'resizable', False)

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
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.progressbar import MDProgressBar

# ==========================================
# CÁC WIDGET VẼ BIỂU ĐỒ & CUSTOM WIDGETS
# ==========================================
class DonutChart(Widget):
    value = NumericProperty(84)
    def on_size(self, *args): self._draw_chart()
    def on_value(self, *args): self._draw_chart()
    def _draw_chart(self):
        self.canvas.clear()
        if self.width == 0 or self.height == 0: return
        with self.canvas:
            Color(0.8, 0.85, 0.8, 1)
            Line(circle=(self.center_x, self.center_y, self.width/2.5, -135, 135), width=12, cap='round')
            Color(0.48, 0.65, 0.48, 1)
            safe_value = min(100, max(0, self.value))
            angle = -135 + (270 * (safe_value / 100))
            Line(circle=(self.center_x, self.center_y, self.width/2.5, -135, angle), width=12, cap='round')

class HabitDonutChart(Widget):
    def on_size(self, *args):
        self.canvas.clear()
        if self.width == 0 or self.height == 0: return
        with self.canvas:
            Color(0.8, 0.85, 0.8, 1)
            Line(circle=(self.center_x, self.center_y, self.width/2.5), width=15)
            angles = [0, 144, 252, 324, 360]
            colors = [(0.25, 0.5, 0.25, 1), (0.4, 0.65, 0.4, 1), (0.55, 0.75, 0.55, 1), (0.7, 0.85, 0.7, 1)]
            for i in range(4):
                Color(*colors[i])
                Line(circle=(self.center_x, self.center_y, self.width/2.5, angles[i], angles[i+1]), width=15)

class SmoothLineChart(Widget):
    data = ListProperty([60, 65, 55, 75, 80, 78, 85, 84, 90, 88])
    def on_size(self, *args):
        self.canvas.clear()
        if not self.data or self.width == 0: return
        step_x = self.width / (len(self.data) - 1)
        scale_y = self.height / 100
        points = []
        for i, val in enumerate(self.data):
            points.extend([self.x + i*step_x, self.y + val*scale_y])
        with self.canvas:
            Color(0.48, 0.65, 0.48, 1)
            Line(points=points, width=2, cap='round', joint='round')

class LineChart(Widget):
    data = ListProperty([4.2, 3.8, 5.1, 3.2, 2.9, 2.1, 3.4])
    max_val = NumericProperty(8)
    def on_size(self, *args):
        self.canvas.clear()
        if not self.data or self.width == 0: return
        step_x = self.width / (len(self.data) - 1)
        scale_y = self.height / self.max_val
        points = []
        for i, val in enumerate(self.data):
            points.extend([self.x + i*step_x, self.y + val*scale_y])
        with self.canvas:
            Color(0.8, 0.85, 0.8, 1)
            Line(points=[self.x, self.y + 5*scale_y, self.right, self.y + 5*scale_y], width=1.5, dash_offset=5, dash_length=5)
            Color(0.48, 0.65, 0.48, 1)
            Line(points=points, width=2)
            for i in range(len(self.data)):
                Ellipse(pos=(points[i*2] - 4, points[i*2+1] - 4), size=(8, 8))

class BarChart(Widget):
    data = ListProperty([60, 70, 68, 85])
    max_val = NumericProperty(100)
    def on_size(self, *args):
        self.canvas.clear()
        if not self.data or self.width == 0: return
        bar_width = (self.width / len(self.data)) * 0.4
        spacing = (self.width / len(self.data)) * 0.6
        scale_y = self.height / self.max_val
        with self.canvas:
            Color(0.48, 0.65, 0.48, 1)
            for i, val in enumerate(self.data):
                x = self.x + i*(bar_width + spacing) + spacing/2
                y = self.y
                h = val * scale_y
                RoundedRectangle(pos=(x, y), size=(bar_width, h), radius=[8, 8, 8, 8])

class HabitItem(ButtonBehavior, BoxLayout):
    habit_id = StringProperty("")
    icon = StringProperty("bus")
    title = StringProperty("Habit")
    xp_reward = NumericProperty(0)
    checked = BooleanProperty(False)

class ExtraTaskItem(MDCard):
    task_id = StringProperty("")
    icon = StringProperty("leaf")
    title = StringProperty("Extra Task")
    xp_reward = NumericProperty(0)

# Khởi tạo thư mục bộ nhớ đệm
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

KV = '''
#:import get_color_from_hex kivy.utils.get_color_from_hex

<HabitItem>:
    orientation: "horizontal"
    size_hint_y: None
    height: "40dp"
    spacing: "10dp"
    disabled: root.checked
    opacity: 0.5 if root.checked else 1.0
    on_release: app.select_daily_habit(self.habit_id, self.title, self.xp_reward, True)
    
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: 0.2, 0.4, 0.2, 1
        size_hint_x: None
        width: "30dp"
    MDLabel:
        text: root.title
        theme_text_color: "Custom"
        text_color: (0.1, 0.1, 0.1, 1) if app.theme_cls.theme_style == "Light" else (1, 1, 1, 1)
        font_style: "Body2"
    MDLabel:
        text: f"+{root.xp_reward} XP"
        theme_text_color: "Custom"
        text_color: (0.3, 0.3, 0.3, 1) if app.theme_cls.theme_style == "Light" else (0.7, 0.7, 0.7, 1)
        font_style: "Caption"
        halign: "right"
        bold: True
    MDIcon:
        icon: "check-circle-outline" if root.checked else "checkbox-blank-circle-outline"
        theme_text_color: "Custom"
        text_color: (0.3, 0.6, 0.3, 1) if root.checked else (0.7, 0.7, 0.7, 1)
        size_hint_x: None
        width: "30dp"

<ExtraTaskItem>:
    orientation: "horizontal"
    size_hint_y: None
    height: "60dp"
    padding: "10dp"
    spacing: "10dp"
    md_bg_color: (0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
    radius: [10]
    elevation: 0
    on_release: app.select_daily_habit(self.task_id, self.title, self.xp_reward, False)
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: 0.3, 0.6, 0.3, 1
        pos_hint: {"center_y": .5}
    MDLabel:
        text: root.title
        font_style: "Body2"
        theme_text_color: "Primary"
    MDLabel:
        text: f"+{root.xp_reward} XP"
        font_style: "Caption"
        bold: True
        halign: "right"
        theme_text_color: "Hint"

<ActiveChallenge@MDCard>:
    size_hint_y: None
    height: "150dp"  
    radius: [20]
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
        spacing: "15dp"
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
                font_style: "Subtitle1"
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
            width: "120dp"
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
                bold: True
        Widget:

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
        font_size: "30sp"
    MDLabel:
        text: root.title
        halign: "center"
        font_style: "Caption"
        theme_text_color: "Secondary" if root.unlocked else "Hint"
        size_hint_y: None
        height: "20dp"
    MDIcon:
        icon: "circle"
        font_size: "10sp"
        halign: "center"
        theme_text_color: "Custom"
        text_color: (0.4, 0.6, 0.4, 1) if root.unlocked else (0,0,0,0)

<SocialFeedItem@MDCard>:
    orientation: "vertical"
    padding: "15dp"
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
            radius: [self.height/2]
        Color:
            rgba: 0.4, 0.6, 0.4, 1
        RoundedRectangle:
            pos: self.pos
            size: (self.width * (self.value / 100.0), self.height) if self.value > 0 else (0, self.height)
            radius: [self.height/2]

<TeamLeaderboardItem@BoxLayout>:
    size_hint_y: None
    height: "60dp"
    spacing: "15dp"
    padding: "10dp"
    rank_text: "1"
    user_name: "Name"
    user_xp: "0 XP"
    progress_val: 0
    is_me: False
    canvas.before:
        Color:
            rgba: (0.82, 0.88, 0.8, 0.6) if root.is_me and app.theme_cls.theme_style == "Light" else ((0.3, 0.4, 0.3, 0.6) if root.is_me else (0,0,0,0))
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [15]
    MDLabel:
        text: root.rank_text
        bold: True
        font_style: "H6"
        size_hint_x: None
        width: "30dp"
        halign: "center"
        theme_text_color: "Custom"
        text_color: (0.4, 0.6, 0.4, 1) if root.rank_text in ["1","2","3"] else (0.6, 0.6, 0.6, 1)
    MDIcon:
        icon: "account-circle"
        theme_text_color: "Custom"
        text_color: 0.4, 0.5, 0.4, 1
        font_size: "35sp"
        size_hint_x: None
        width: "40dp"
    BoxLayout:
        orientation: "vertical"
        size_hint_x: 0.4
        MDLabel:
            text: root.user_name + (" (you)" if root.is_me else "")
            bold: True
            theme_text_color: "Primary"
        MDLabel:
            text: root.user_xp
            font_style: "Caption"
            theme_text_color: "Hint"
    AnchorLayout:
        anchor_x: "right"
        anchor_y: "center"
        size_hint_x: 0.6
        CustomProgressBar:
            size_hint: None, None
            size: "120dp", "8dp"
            value: root.progress_val

<StatCard@MDCard>:
    orientation: "vertical"
    padding: "15dp"
    spacing: "5dp"
    radius: [20]
    elevation: 0
    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
    icon: "leaf"
    value: "0"
    desc: "Desc"
    MDIcon:
        icon: root.icon
        halign: "center"
        font_size: "30sp"
        theme_text_color: "Custom"
        text_color: 0.4, 0.6, 0.4, 1
        canvas.before:
            Color:
                rgba: (0.82, 0.88, 0.82, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.3, 0.2, 1)
            Ellipse:
                pos: self.center_x - 25, self.center_y - 25
                size: 50, 50
    MDLabel:
        text: root.value
        halign: "center"
        font_style: "H5"
        bold: True
        theme_text_color: "Primary"
    MDLabel:
        text: root.desc
        halign: "center"
        font_style: "Caption"
        theme_text_color: "Hint"

<GoalItem@BoxLayout>:
    orientation: "vertical"
    size_hint_y: None
    height: "50dp"
    title: ""
    progress_text: ""
    value: 0
    BoxLayout:
        MDLabel:
            text: root.title
            font_style: "Caption"
            theme_text_color: "Primary"
        MDLabel:
            text: root.progress_text
            font_style: "Caption"
            halign: "right"
            bold: True
            theme_text_color: "Hint"
    CustomProgressBar:
        size_hint_y: None
        height: "8dp"
        value: root.value

<PrefItem@MDCard>:
    orientation: "horizontal"
    padding: "10dp"
    spacing: "10dp"
    radius: [15]
    elevation: 0
    size_hint_y: None
    height: "60dp"
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
            font_style: "Subtitle2"
            bold: True
            theme_text_color: "Primary"

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
                size_hint: None, None
                size: "420dp", "520dp"
                padding: "28dp"
                spacing: "18dp"
                orientation: "vertical"
                radius: [24, 24, 24, 24]
                elevation: 4
                md_bg_color: app.theme_cls.bg_light
                BoxLayout:
                    orientation: "horizontal"
                    size_hint_y: None
                    height: "50dp"
                    spacing: "12dp"
                    pos_hint: {"center_x": 0.5}
                    MDIcon:
                        icon: "leaf"
                        text_color: 0.18, 0.49, 0.2, 1
                        theme_text_color: "Custom"
                        font_size: "40sp"
                    MDLabel:
                        text: "Eco Space"
                        bold: True
                        font_style: "H4"
                        theme_text_color: "Primary"
                MDLabel:
                    text: "Hệ thống quản lý lối sống xanh"
                    font_style: "Caption"
                    halign: "center"
                    theme_text_color: "Secondary"
                Widget:
                    size_hint_y: None
                    height: "10dp"
                MDTextField:
                    id: login_user
                    hint_text: "Tên đăng nhập hoặc Email"
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
                    height: "5dp"
                MDFillRoundFlatButton:
                    text: "ĐĂNG NHẬP VÀO HỆ THỐNG"
                    size_hint_x: 1
                    md_bg_color: 0.18, 0.49, 0.2, 1
                    radius: [8, 8, 8, 8]
                    on_release: app.process_login()

    Screen:
        name: "main_app_screen"
        BoxLayout:
            orientation: "horizontal"
            canvas.before:
                Color:
                    rgba: (0.95, 0.96, 0.94, 1) if app.theme_cls.theme_style == "Light" else (0.05, 0.05, 0.05, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            
            # --- SIDEBAR ---
            BoxLayout:
                orientation: "vertical"
                size_hint_x: 0.25
                padding: "16dp"
                spacing: "8dp"
                canvas.before:
                    Color:
                        rgba: (0.91, 0.93, 0.90, 1) if app.theme_cls.theme_style == "Light" else (0.12, 0.12, 0.12, 1)
                    Rectangle:
                        pos: self.pos
                        size: self.size
                
                # Logo
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
                            font_style: "Subtitle1"
                            theme_text_color: "Primary"
                        MDLabel:
                            text: "Impact Monitor"
                            font_style: "Caption"
                            theme_text_color: "Secondary"
                
                Widget:
                    size_hint_y: None
                    height: "10dp"

                # Streak Card
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
                        text: "72% to next milestone"
                        font_style: "Caption"
                        theme_text_color: "Hint"
                        font_size: "10sp"

                Widget:
                    size_hint_y: None
                    height: "15dp"

                # Navigation
                SidebarButton:
                    id: nav_dashboard
                    icon: "view-dashboard"
                    text: "Dashboard"
                    on_release: app.switch_tab("tab_dashboard", self)
                SidebarButton:
                    id: nav_gamification
                    icon: "trophy-outline"
                    text: "Gamification"
                    on_release: app.switch_tab("tab_gamification", self)
                SidebarButton:
                    id: nav_social
                    icon: "account-group-outline"
                    text: "Social & Feed"
                    on_release: app.switch_tab("tab_social", self)
                SidebarButton:
                    id: nav_groups
                    icon: "account-multiple"
                    text: "Team & Groups"
                    on_release: app.switch_tab("tab_groups", self)
                SidebarButton:
                    id: nav_stats
                    icon: "account-details"
                    text: "Profile & Settings"
                    on_release: app.switch_tab("tab_stats", self)
                
                Widget:
                
                # User Profile Bottom
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
                            text: "Lv. 12"
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

            # --- NỘI DUNG CHÍNH ---
            BoxLayout:
                orientation: "vertical"
                size_hint_x: 0.75
                padding: "20dp"
                spacing: "15dp"
                
                BoxLayout:
                    size_hint_y: None
                    height: "50dp"
                    orientation: "horizontal"
                    BoxLayout:
                        orientation: "vertical"
                        MDLabel:
                            id: title_page
                            text: "Dashboard"
                            font_style: "H5"
                            bold: True
                            theme_text_color: "Primary"
                        MDLabel:
                            id: subtitle_page
                            text: "Quản lý lối sống xanh"
                            font_style: "Caption"
                            theme_text_color: "Hint"
                
                ScreenManager:
                    id: sm
                    on_current: app.update_title_label(self.current)

                    # === 1. DASHBOARD CHÍNH ===
                    Screen:
                        name: "tab_dashboard"
                        ScrollView:
                            BoxLayout:
                                orientation: "vertical"
                                spacing: "15dp"
                                size_hint_y: None
                                height: self.minimum_height
                                MDCard:
                                    radius: [20,]
                                    size_hint_y: None
                                    height: "260dp"
                                    padding: "20dp"
                                    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                    elevation: 0
                                    orientation: "vertical"
                                    
                                    BoxLayout:
                                        orientation: "horizontal"
                                        size_hint_y: None
                                        height: "40dp"
                                        BoxLayout:
                                            orientation: "vertical"
                                            MDLabel:
                                                text: "Daily Eco Score"
                                                font_style: "Subtitle1"
                                                bold: True
                                                theme_text_color: "Primary"
                                            MDLabel:
                                                text: "Personal impact index"
                                                font_style: "Caption"
                                                theme_text_color: "Hint"
                                        MDRoundFlatButton:
                                            text: "Top 15%"
                                            line_color: 0,0,0,0
                                            md_bg_color: 0.8, 0.85, 0.8, 1
                                            text_color: 0.3, 0.5, 0.3, 1
                                    
                                    AnchorLayout:
                                        anchor_x: "center"
                                        anchor_y: "center"
                                        DonutChart:
                                            id: donut_chart
                                            size_hint: None, None
                                            size: "160dp", "160dp"
                                            value: 84
                                        BoxLayout:
                                            orientation: "vertical"
                                            size_hint: None, None
                                            size: "80dp", "80dp"
                                            MDLabel:
                                                id: eco_score_label
                                                text: "84"
                                                font_style: "H4"
                                                bold: True
                                                halign: "center"
                                                theme_text_color: "Custom"
                                                text_color: (0, 0, 0, 1) if app.theme_cls.theme_style == "Light" else (1, 1, 1, 1)
                                            MDLabel:
                                                text: "Eco Score"
                                                font_style: "Caption"
                                                halign: "center"
                                                theme_text_color: "Hint"
                                            MDLabel:
                                                id: eco_score_today_label
                                                text: "+8 today"
                                                font_style: "Caption"
                                                halign: "center"
                                                theme_text_color: "Custom"
                                                text_color: 0.4, 0.6, 0.4, 1
                                    
                                    BoxLayout:
                                        orientation: "horizontal"
                                        size_hint_y: None
                                        height: "60dp"
                                        spacing: "10dp"
                                        
                                        MDCard:
                                            radius: [10,]
                                            md_bg_color: (0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
                                            elevation: 0
                                            orientation: "vertical"
                                            padding: "5dp"
                                            MDLabel:
                                                text: "3.4kg"
                                                font_style: "Subtitle2"
                                                bold: True
                                                halign: "center"
                                                theme_text_color: "Primary"
                                            MDLabel:
                                                text: "Carbon"
                                                font_style: "Caption"
                                                halign: "center"
                                                theme_text_color: "Hint"
                                                
                                        MDCard:
                                            radius: [10,]
                                            md_bg_color: (0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
                                            elevation: 0
                                            orientation: "vertical"
                                            padding: "5dp"
                                            MDLabel:
                                                text: "87L"
                                                font_style: "Subtitle2"
                                                bold: True
                                                halign: "center"
                                                theme_text_color: "Primary"
                                            MDLabel:
                                                text: "Water"
                                                font_style: "Caption"
                                                halign: "center"
                                                theme_text_color: "Hint"
                                                
                                        MDCard:
                                            radius: [10,]
                                            md_bg_color: (0.85, 0.88, 0.84, 1) if app.theme_cls.theme_style == "Light" else (0.2, 0.2, 0.2, 1)
                                            elevation: 0
                                            orientation: "vertical"
                                            padding: "5dp"
                                            MDLabel:
                                                text: "4.2kWh"
                                                font_style: "Subtitle2"
                                                bold: True
                                                halign: "center"
                                                theme_text_color: "Primary"
                                            MDLabel:
                                                text: "Energy"
                                                font_style: "Caption"
                                                halign: "center"
                                                theme_text_color: "Hint"

                                BoxLayout:
                                    orientation: "horizontal"
                                    size_hint_y: None
                                    height: "220dp"
                                    spacing: "15dp"
                                    MDCard:
                                        radius: [20,]
                                        padding: "15dp"
                                        md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                        elevation: 0
                                        orientation: "vertical"
                                        BoxLayout:
                                            size_hint_y: None
                                            height: "40dp"
                                            BoxLayout:
                                                orientation: "vertical"
                                                MDLabel:
                                                    text: "Carbon Footprint"
                                                    bold: True
                                                    theme_text_color: "Primary"
                                                MDLabel:
                                                    text: "Daily kg CO2 - This week"
                                                    font_style: "Caption"
                                                    theme_text_color: "Hint"
                                            MDLabel:
                                                text: "↓ 18%"
                                                halign: "right"
                                                bold: True
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
                                                    halign: "center"
                                                MDLabel:
                                                    text: "6"
                                                    font_style: "Caption"
                                                    halign: "center"
                                                MDLabel:
                                                    text: "4"
                                                    font_style: "Caption"
                                                    halign: "center"
                                                MDLabel:
                                                    text: "2"
                                                    font_style: "Caption"
                                                    halign: "center"
                                                MDLabel:
                                                    text: "0"
                                                    font_style: "Caption"
                                                    halign: "center"
                                            
                                            BoxLayout:
                                                orientation: "vertical"
                                                LineChart:
                                                    data: [4.2, 3.8, 5.1, 3.2, 2.9, 2.1, 3.4]
                                                    max_val: 8
                                                BoxLayout:
                                                    size_hint_y: None
                                                    height: "20dp"
                                                    MDLabel:
                                                        text: "Mon"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "Tue"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "Wed"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "Thu"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "Fri"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "Sat"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "Sun"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    
                                    MDCard:
                                        radius: [20,]
                                        padding: "15dp"
                                        md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                        elevation: 0
                                        orientation: "vertical"
                                        BoxLayout:
                                            size_hint_y: None
                                            height: "40dp"
                                            BoxLayout:
                                                orientation: "vertical"
                                                MDLabel:
                                                    text: "Weekly Score"
                                                    bold: True
                                                    theme_text_color: "Primary"
                                                MDLabel:
                                                    text: "Eco score trend"
                                                    font_style: "Caption"
                                                    theme_text_color: "Hint"
                                            MDIcon:
                                                icon: "arrow-top-right"
                                                halign: "right"
                                                theme_text_color: "Hint"
                                        
                                        BoxLayout:
                                            orientation: "horizontal"
                                            BoxLayout:
                                                orientation: "vertical"
                                                size_hint_x: None
                                                width: "25dp"
                                                MDLabel:
                                                    text: "100"
                                                    font_style: "Caption"
                                                    halign: "center"
                                                MDLabel:
                                                    text: "75"
                                                    font_style: "Caption"
                                                    halign: "center"
                                                MDLabel:
                                                    text: "50"
                                                    font_style: "Caption"
                                                    halign: "center"
                                                MDLabel:
                                                    text: "25"
                                                    font_style: "Caption"
                                                    halign: "center"
                                                MDLabel:
                                                    text: "0"
                                                    font_style: "Caption"
                                                    halign: "center"
                                            
                                            BoxLayout:
                                                orientation: "vertical"
                                                BarChart:
                                                    data: [60, 70, 68, 85]
                                                    max_val: 100
                                                BoxLayout:
                                                    size_hint_y: None
                                                    height: "20dp"
                                                    MDLabel:
                                                        text: "W1"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "W2"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "W3"
                                                        font_style: "Caption"
                                                        halign: "center"
                                                    MDLabel:
                                                        text: "W4"
                                                        font_style: "Caption"
                                                        halign: "center"

                                MDCard:
                                    radius: [20,]
                                    size_hint_y: None
                                    height: "320dp"
                                    padding: "20dp"
                                    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                    elevation: 0
                                    orientation: "vertical"
                                    spacing: "15dp"
                                    
                                    BoxLayout:
                                        size_hint_y: None
                                        height: "40dp"
                                        orientation: "horizontal"
                                        BoxLayout:
                                            orientation: "vertical"
                                            MDLabel:
                                                text: "Today's Habits"
                                                font_style: "Subtitle1"
                                                bold: True
                                                theme_text_color: "Custom"
                                                text_color: (0, 0, 0, 1) if app.theme_cls.theme_style == "Light" else (1, 1, 1, 1)
                                            MDLabel:
                                                id: habit_progress_text
                                                text: "0/5 completed"
                                                font_style: "Caption"
                                                theme_text_color: "Custom"
                                                text_color: (0.4, 0.4, 0.4, 1) if app.theme_cls.theme_style == "Light" else (0.6, 0.6, 0.6, 1)
                                        BoxLayout:
                                            orientation: "horizontal"
                                            size_hint_x: 0.4
                                            MDProgressBar:
                                                id: habit_progress_bar
                                                value: 0
                                                color: 0.48, 0.65, 0.48, 1
                                            MDLabel:
                                                id: habit_percentage_text
                                                text: "0%"
                                                size_hint_x: None
                                                width: "40dp"
                                                halign: "right"
                                                font_style: "Caption"
                                                bold: True
                                                theme_text_color: "Custom"
                                                text_color: (0, 0, 0, 1) if app.theme_cls.theme_style == "Light" else (1, 1, 1, 1)

                                    BoxLayout:
                                        orientation: "vertical"
                                        spacing: "5dp"
                                        HabitItem:
                                            id: habit_1
                                            habit_id: "habit_1"
                                            icon: "bus"
                                            title: "Take public transit"
                                            xp_reward: 50
                                            checked: False
                                        MDSeparator:
                                            color: 0.8, 0.85, 0.8, 1
                                        HabitItem:
                                            id: habit_2
                                            habit_id: "habit_2"
                                            icon: "leaf"
                                            title: "Meatless meal"
                                            xp_reward: 30
                                            checked: False
                                        MDSeparator:
                                            color: 0.8, 0.85, 0.8, 1
                                        HabitItem:
                                            id: habit_3
                                            habit_id: "habit_3"
                                            icon: "shower-head"
                                            title: "5-min cold shower"
                                            xp_reward: 20
                                            checked: False
                                        MDSeparator:
                                            color: 0.8, 0.85, 0.8, 1
                                        HabitItem:
                                            id: habit_4
                                            habit_id: "habit_4"
                                            icon: "shopping"
                                            title: "Reusable bag shopping"
                                            xp_reward: 25
                                            checked: False
                                        MDSeparator:
                                            color: 0.8, 0.85, 0.8, 1
                                        HabitItem:
                                            id: habit_5
                                            habit_id: "habit_5"
                                            icon: "bike"
                                            title: "Cycle or walk"
                                            xp_reward: 40
                                            checked: False

                    # === 2. GHI NHẬN HÀNH ĐỘNG ===
                    Screen:
                        name: "tab_ghi_nhan"
                        BoxLayout:
                            orientation: "vertical"
                            spacing: "12dp"
                            MDCard:
                                size_hint_y: 0.85
                                radius: [14, 14, 14, 14]
                                padding: "16dp"
                                spacing: "12dp"
                                elevation: 2
                                orientation: "vertical"
                                md_bg_color: app.theme_cls.bg_light
                                MDLabel:
                                    id: status_label
                                    text: "Hệ thống: Sẵn sàng xác nhận hình ảnh"
                                    halign: "center"
                                    bold: True
                                    font_style: "Subtitle2"
                                    theme_text_color: "Primary"
                                    size_hint_y: None
                                    height: "30dp"
                                SafeAnchorLayout:
                                    anchor_x: "center"
                                    anchor_y: "center"
                                    size_hint_y: None
                                    height: "240dp"
                                    Image:
                                        id: preview_image
                                        source: ""
                                        size_hint: None, None
                                        size: "360dp", "220dp"
                               
                                BoxLayout:
                                    size_hint_y: None
                                    height: "40dp"
                                    spacing: "12dp"
                                    MDFillRoundFlatButton:
                                        id: btn_ai_scan
                                        text: "XÁC NHẬN ẢNH & NHẬN ĐIỂM"
                                        md_bg_color: 0.1, 0.45, 0.8, 1
                                        disabled: True
                                        radius: [8, 8, 8, 8]
                                        on_release: app.instant_reward()
                                    MDRaisedButton:
                                        id: delete_image_btn
                                        text: "XÓA ẢNH"
                                        md_bg_color: 0.8, 0.2, 0.2, 1
                                        opacity: 0
                                        disabled: True
                                        radius: [8, 8, 8, 8]
                                        on_release: app.clear_current_image()
                            BoxLayout:
                                size_hint_y: None
                                height: "50dp"
                                spacing: "12dp"
                                MDFillRoundFlatIconButton:
                                    icon: "camera"
                                    text: "CHỤP ẢNH (CAMERA)"
                                    size_hint_x: 0.5
                                    md_bg_color: 0.18, 0.49, 0.2, 1
                                    radius: [8, 8, 8, 8]
                                    on_release: app.open_camera_popup()
                                MDFillRoundFlatIconButton:
                                    icon: "upload"
                                    text: "TẢI LÊN (UPLOAD)"
                                    size_hint_x: 0.5
                                    md_bg_color: 0.25, 0.35, 0.5, 1
                                    radius: [8, 8, 8, 8]
                                    on_release: app.trigger_upload_macos()

                    # === 3. GAMIFICATION CHÍNH ===
                    Screen:
                        name: "tab_gamification"
                        ScrollView:
                            BoxLayout:
                                orientation: "vertical"
                                spacing: "20dp"
                                padding: "5dp"
                                size_hint_y: None
                                height: self.minimum_height
                                
                                MDCard:
                                    radius: [20]
                                    size_hint_y: None
                                    height: "100dp"
                                    padding: "20dp"
                                    md_bg_color: (0.85, 0.9, 0.85, 1) if app.theme_cls.theme_style == "Light" else (0.18, 0.25, 0.18, 1)
                                    elevation: 0
                                    orientation: "horizontal"
                                    spacing: "15dp"
                                    MDIcon:
                                        icon: "lightning-bolt"
                                        theme_text_color: "Custom"
                                        text_color: 1, 1, 1, 1
                                        canvas.before:
                                            Color:
                                                rgba: 0.5, 0.7, 0.5, 1
                                            Ellipse:
                                                pos: self.x - 5, self.y - 5
                                                size: self.width + 10, self.height + 10
                                    BoxLayout:
                                        orientation: "vertical"
                                        spacing: "5dp"
                                        MDLabel:
                                            id: gami_level_title
                                            text: "Level 12 — Eco Ranger"
                                            bold: True
                                            font_style: "Subtitle1"
                                        MDLabel:
                                            id: gami_xp_text
                                            text: "2840 / 3000 XP · 160 to Level 13"
                                            font_style: "Caption"
                                            theme_text_color: "Hint"
                                        MDProgressBar:
                                            id: gami_main_progress
                                            value: 80
                                            color: 0.4, 0.6, 0.4, 1
                                    BoxLayout:
                                        orientation: "horizontal"
                                        size_hint_x: None
                                        width: "80dp"
                                        MDIcon:
                                            icon: "fire"
                                            theme_text_color: "Custom"
                                            text_color: 0.9, 0.4, 0.1, 1
                                        MDLabel:
                                            id: gami_streak_text
                                            text: "12 streak"
                                            bold: True
                                            font_style: "Caption"

                                MDLabel:
                                    text: "Monthly Challenges"
                                    bold: True
                                    font_style: "Subtitle1"
                                    size_hint_y: None
                                    height: "30dp"
                                ActiveChallenge:
                                    c_title: "Plastic-Free July"
                                    c_sub: "Avoid single-use plastics for 30 days"
                                    c_icon: "recycle"
                                    c_prog_text: "21/30 days"
                                    c_prog_val: 68
                                    c_tag: "500 XP + Badge"
                                ActiveChallenge:
                                    c_title: "Cycle to Work"
                                    c_sub: "Commute by bike 15 times"
                                    c_icon: "bike"
                                    c_prog_text: "6/15 days"
                                    c_prog_val: 40
                                    c_tag: "300 XP"
                                ActiveChallenge:
                                    c_title: "Meatless Month"
                                    c_sub: "Log 20 plant-based meals"
                                    c_icon: "food-apple"
                                    c_prog_text: "17/20 days"
                                    c_prog_val: 85
                                    c_tag: "400 XP + Badge"
                                
                                MDLabel:
                                    text: "Nhiệm vụ thêm (Extra Tasks)"
                                    bold: True
                                    font_style: "Subtitle1"
                                    size_hint_y: None
                                    height: "30dp"
                                MDCard:
                                    radius: [20]
                                    size_hint_y: None
                                    height: "300dp"
                                    padding: "15dp"
                                    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                    elevation: 0
                                    ScrollView:
                                        MDList:
                                            id: extra_tasks_list
                                            spacing: "10dp"

                                MDCard:
                                    radius: [20]
                                    size_hint_y: None
                                    height: "320dp"
                                    padding: "20dp"
                                    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                    elevation: 0
                                    orientation: "vertical"
                                    spacing: "15dp"
                                    MDLabel:
                                        text: "🏆 Trophy Case"
                                        bold: True
                                        font_style: "Subtitle1"
                                        size_hint_y: None
                                        height: "30dp"
                                    GridLayout:
                                        id: trophy_grid
                                        cols: 5
                                        spacing: "15dp"
                                    MDLabel:
                                        id: trophy_count_label
                                        text: "3 of 10 trophies unlocked"
                                        halign: "center"
                                        font_style: "Caption"
                                        theme_text_color: "Hint"
                                        size_hint_y: None
                                        height: "20dp"

                    # === 4. SOCIAL & FEED ===
                    Screen:
                        name: "tab_social"
                        BoxLayout:
                            orientation: "horizontal"
                            spacing: "15dp"
                            
                            # Cột Bạn Bè
                            MDCard:
                                size_hint_x: 0.35
                                radius: [20]
                                padding: "20dp"
                                orientation: "vertical"
                                md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                elevation: 0
                                spacing: "10dp"
                                MDLabel:
                                    text: "Hệ thống Bạn Bè"
                                    bold: True
                                    font_style: "Subtitle1"
                                    size_hint_y: None
                                    height: "30dp"
                                ScrollView:
                                    MDList:
                                        id: friends_list
                                        OneLineAvatarIconListItem:
                                            text: "Aria Chen (2,840 XP)"
                                            IconLeftWidget:
                                                icon: "account-circle"
                                                theme_text_color: "Custom"
                                                text_color: 0.4, 0.6, 0.4, 1
                                        OneLineAvatarIconListItem:
                                            text: "Bảo Minh (1,150 XP)"
                                            IconLeftWidget:
                                                icon: "account-circle"
                                                theme_text_color: "Custom"
                                                text_color: 0.4, 0.6, 0.4, 1
                                        OneLineAvatarIconListItem:
                                            text: "Hải Đăng (900 XP)"
                                            IconLeftWidget:
                                                icon: "account-circle"
                                                theme_text_color: "Custom"
                                                text_color: 0.4, 0.6, 0.4, 1
                                
                            # Cột Bảng tin
                            MDCard:
                                size_hint_x: 0.65
                                radius: [20]
                                padding: "20dp"
                                orientation: "vertical"
                                md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                elevation: 0
                                spacing: "10dp"
                                MDLabel:
                                    text: "Bảng tin hoạt động (Eco Feed)"
                                    bold: True
                                    font_style: "Subtitle1"
                                    size_hint_y: None
                                    height: "30dp"
                                ScrollView:
                                    BoxLayout:
                                        orientation: "vertical"
                                        spacing: "15dp"
                                        size_hint_y: None
                                        height: self.minimum_height
                                        
                                        SocialFeedItem:
                                            user_name: "Bảo Minh"
                                            action_text: "vừa đạp xe 5km đi làm."
                                            like_count: "12"
                                        SocialFeedItem:
                                            user_name: "Hải Đăng"
                                            action_text: "vừa phân loại 2kg rác hữu cơ."
                                            like_count: "5"
                                        SocialFeedItem:
                                            user_name: "Ngọc Anh"
                                            action_text: "trồng 3 cây xanh trong vườn nhà."
                                            like_count: "15"
                                        SocialFeedItem:
                                            user_name: "Hoàng Tú"
                                            action_text: "tái chế 10 vỏ chai nhựa."
                                            like_count: "8"

                    # === 5. TEAM & GROUPS ===
                    Screen:
                        name: "tab_groups"
                        ScrollView:
                            BoxLayout:
                                orientation: "vertical"
                                spacing: "20dp"
                                padding: "5dp"
                                size_hint_y: None
                                height: self.minimum_height
                                
                                # --- BẢNG XẾP HẠNG NỘI BỘ ---
                                MDCard:
                                    radius: [20]
                                    size_hint_y: None
                                    height: "440dp"
                                    padding: "20dp"
                                    spacing: "10dp"
                                    orientation: "vertical"
                                    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                    elevation: 0
                                    
                                    MDLabel:
                                        text: "Bảng xếp hạng đóng góp (Team Leaderboard)"
                                        bold: True
                                        font_style: "Subtitle1"
                                        size_hint_y: None
                                        height: "40dp"
                                        
                                    TeamLeaderboardItem:
                                        rank_text: "1"
                                        user_name: "Marcus T."
                                        user_xp: "4,280 XP"
                                        progress_val: 100
                                        
                                    TeamLeaderboardItem:
                                        rank_text: "2"
                                        user_name: "Yuki S."
                                        user_xp: "3,940 XP"
                                        progress_val: 92
                                        
                                    TeamLeaderboardItem:
                                        rank_text: "3"
                                        user_name: "Aria Chen"
                                        user_xp: "3,680 XP"
                                        progress_val: 86
                                        is_me: True
                                        
                                    TeamLeaderboardItem:
                                        rank_text: "4"
                                        user_name: "Camille R."
                                        user_xp: "3,210 XP"
                                        progress_val: 75
                                        
                                    TeamLeaderboardItem:
                                        rank_text: "5"
                                        user_name: "Dev P."
                                        user_xp: "2,990 XP"
                                        progress_val: 69

                                # --- THỬ THÁCH CHUNG (COMMUNITY CHALLENGE) ---
                                MDCard:
                                    radius: [20]
                                    size_hint_y: None
                                    height: "170dp"  
                                    padding: "20dp"
                                    spacing: "15dp"
                                    orientation: "vertical"
                                    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                    elevation: 0
                                    
                                    BoxLayout:
                                        orientation: "horizontal"
                                        size_hint_y: None
                                        height: "30dp"
                                        MDIcon:
                                            icon: "leaf"
                                            theme_text_color: "Custom"
                                            text_color: 0.3, 0.6, 0.3, 1
                                            size_hint_x: None
                                            width: "30dp"
                                        MDLabel:
                                            text: "Thử thách chung (Team Target)"
                                            bold: True
                                            font_style: "Subtitle1"
                                            
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
                                                radius: [15]
                                        padding: "10dp"
                                        MDLabel:
                                            text: "🌍 Mục tiêu Nhóm 20,000 Điểm"
                                            bold: True
                                            theme_text_color: "Primary"
                                        MDLabel:
                                            text: "Cùng nhau đạt 20,000 XP tổng để nhận phần thưởng Nhóm xuất sắc."
                                            font_style: "Caption"
                                            theme_text_color: "Hint"
                                            
                                    BoxLayout:
                                        orientation: "vertical"
                                        size_hint_y: None
                                        height: "30dp"
                                        BoxLayout:
                                            orientation: "horizontal"
                                            MDLabel:
                                                text: "18,100 / 20,000 XP"
                                                font_style: "Caption"
                                                theme_text_color: "Hint"
                                            MDLabel:
                                                text: "90%"
                                                font_style: "Caption"
                                                bold: True
                                                halign: "right"
                                                theme_text_color: "Hint"
                                        CustomProgressBar:
                                            value: 90

                                # --- NHIỆM VỤ TUẦN VÀ LIVE IMPACT ---
                                MDCard:
                                    radius: [20]
                                    size_hint_y: None
                                    height: "220dp"
                                    padding: "20dp"
                                    spacing: "15dp"
                                    orientation: "vertical"
                                    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                    elevation: 0
                                    
                                    BoxLayout:
                                        orientation: "horizontal"
                                        size_hint_y: None
                                        height: "30dp"
                                        MDIcon:
                                            icon: "sprout"
                                            theme_text_color: "Custom"
                                            text_color: 0.3, 0.6, 0.3, 1
                                            size_hint_x: None
                                            width: "30dp"
                                        MDLabel:
                                            text: "Nhiệm vụ & Thông số Tuần"
                                            bold: True
                                            font_style: "Subtitle1"
                                            
                                    BoxLayout:
                                        orientation: "horizontal"
                                        MDLabel:
                                            text: "Trồng và Chăm sóc cây xanh"
                                            theme_text_color: "Hint"
                                            font_style: "Body2"
                                        MDLabel:
                                            text: "32/50 cây"
                                            bold: True
                                            halign: "right"
                                            theme_text_color: "Primary"
                                            
                                    BoxLayout:
                                        orientation: "horizontal"
                                        MDLabel:
                                            text: "Tái chế rác nhựa toàn nhóm"
                                            theme_text_color: "Hint"
                                            font_style: "Body2"
                                        MDLabel:
                                            text: "12.4 kg"
                                            bold: True
                                            halign: "right"
                                            theme_text_color: "Primary"
                                            
                                    BoxLayout:
                                        orientation: "horizontal"
                                        MDLabel:
                                            text: "Lượt tương tác nội bộ"
                                            theme_text_color: "Hint"
                                            font_style: "Body2"
                                        MDLabel:
                                            text: "284"
                                            bold: True
                                            halign: "right"
                                            theme_text_color: "Primary"
                                            
                                    BoxLayout:
                                        orientation: "horizontal"
                                        MDLabel:
                                            text: "Tổng số hành động đã log"
                                            theme_text_color: "Hint"
                                            font_style: "Body2"
                                        MDLabel:
                                            text: "520"
                                            bold: True
                                            halign: "right"
                                            theme_text_color: "Primary"


                    # === 6. PROFILE & SETTINGS ===
                    Screen:
                        name: "tab_stats"
                        ScrollView:
                            BoxLayout:
                                orientation: "vertical"
                                spacing: "15dp"
                                size_hint_y: None
                                height: self.minimum_height
                                
                                # Hàng 1: Profile Header Card
                                MDCard:
                                    radius: [20]
                                    size_hint_y: None
                                    height: "220dp"
                                    padding: "20dp"
                                    orientation: "vertical"
                                    md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                    elevation: 0
                                    
                                    BoxLayout:
                                        orientation: "horizontal"
                                        spacing: "20dp"
                                        size_hint_y: None
                                        height: "80dp"
                                        
                                        MDIcon:
                                            icon: "account-circle"
                                            font_size: "80sp"
                                            size_hint_x: None
                                            width: "80dp"
                                            theme_text_color: "Custom"
                                            text_color: 0.4, 0.5, 0.4, 1
                                            
                                        BoxLayout:
                                            orientation: "vertical"
                                            spacing: "5dp"
                                            MDLabel:
                                                id: profile_name_label
                                                text: "Aria Chen"
                                                font_style: "H4"
                                                bold: True
                                                theme_text_color: "Primary"
                                            MDLabel:
                                                id: profile_location_label
                                                text: "San Francisco, CA · Member since Jan 2025"
                                                font_style: "Caption"
                                                theme_text_color: "Hint"
                                            BoxLayout:
                                                orientation: "horizontal"
                                                spacing: "10dp"
                                                size_hint_y: None
                                                height: "20dp"
                                                MDLabel:
                                                    text: "🌿 Eco Ranger"
                                                    font_style: "Caption"
                                                    bold: True
                                                    theme_text_color: "Custom"
                                                    text_color: 0.3, 0.6, 0.3, 1
                                                MDLabel:
                                                    text: "Level 12"
                                                    font_style: "Caption"
                                                    theme_text_color: "Hint"
                                                MDLabel:
                                                    text: "🔥 12-day streak"
                                                    font_style: "Caption"
                                                    bold: True
                                                    theme_text_color: "Custom"
                                                    text_color: 0.9, 0.5, 0.1, 1
                                        AnchorLayout:
                                            anchor_x: "right"
                                            anchor_y: "top"
                                            size_hint_x: 0.3
                                            MDRoundFlatIconButton:
                                                icon: "pencil"
                                                text: "Edit"
                                                text_color: (0.1, 0.1, 0.1, 1) if app.theme_cls.theme_style == "Light" else (0.9, 0.9, 0.9, 1)
                                                icon_color: (0.1, 0.1, 0.1, 1) if app.theme_cls.theme_style == "Light" else (0.9, 0.9, 0.9, 1)
                                                md_bg_color: 0,0,0,0
                                                line_color: 0.7, 0.7, 0.7, 1
                                                on_release: app.open_edit_profile_popup()
                                                
                                    Widget:
                                        size_hint_y: None
                                        height: "20dp"
                                        
                                    MDLabel:
                                        text: "30-day Eco Score activity"
                                        font_style: "Caption"
                                        theme_text_color: "Hint"
                                        size_hint_y: None
                                        height: "20dp"
                                    SmoothLineChart:
                                        size_hint_y: 1
                                        
                                # Hàng 2: Bốn thẻ Stats
                                GridLayout:
                                    cols: 4
                                    spacing: "15dp"
                                    size_hint_y: None
                                    height: "140dp"
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
                                        
                                # Hàng 3: Badge Collection & Personal Goals
                                BoxLayout:
                                    orientation: "horizontal"
                                    spacing: "15dp"
                                    size_hint_y: None
                                    height: "280dp"
                                    
                                    # Badge Collection
                                    MDCard:
                                        radius: [20]
                                        padding: "20dp"
                                        orientation: "vertical"
                                        md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                        elevation: 0
                                        BoxLayout:
                                            orientation: "horizontal"
                                            size_hint_y: None
                                            height: "30dp"
                                            MDIcon:
                                                icon: "trophy-outline"
                                                theme_text_color: "Custom"
                                                text_color: 0.3, 0.6, 0.3, 1
                                                size_hint_x: None
                                                width: "30dp"
                                            MDLabel:
                                                text: "Badge Collection"
                                                bold: True
                                                font_style: "Subtitle1"
                                        Widget:
                                            size_hint_y: None
                                            height: "10dp"
                                        GridLayout:
                                            cols: 3
                                            spacing: "10dp"
                                            BadgeItem:
                                                icon: "seed"
                                                title: "Seedling"
                                                unlocked: True
                                            BadgeItem:
                                                icon: "water" 
                                                title: "Water Guardian"
                                                unlocked: True
                                            BadgeItem:
                                                icon: "leaf"
                                                title: "Carbon Cutter"
                                                unlocked: True
                                            BadgeItem:
                                                icon: "fire"
                                                title: "Streak Master"
                                                unlocked: False
                                            BadgeItem:
                                                icon: "bike"
                                                title: "Green Commuter"
                                                unlocked: False
                                            BadgeItem:
                                                icon: "recycle"
                                                title: "Zero Waste"
                                                unlocked: False
                                        MDLabel:
                                            text: "3 of 6 badges unlocked"
                                            font_style: "Caption"
                                            theme_text_color: "Hint"
                                            halign: "center"
                                            size_hint_y: None
                                            height: "30dp"
                                            
                                    # Personal Goals
                                    MDCard:
                                        radius: [20]
                                        padding: "20dp"
                                        spacing: "10dp"
                                        orientation: "vertical"
                                        md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                        elevation: 0
                                        BoxLayout:
                                            orientation: "horizontal"
                                            size_hint_y: None
                                            height: "30dp"
                                            MDIcon:
                                                icon: "chart-timeline-variant"
                                                theme_text_color: "Custom"
                                                text_color: 0.3, 0.6, 0.3, 1
                                                size_hint_x: None
                                                width: "30dp"
                                            MDLabel:
                                                text: "Personal Goals"
                                                bold: True
                                                font_style: "Subtitle1"
                                        GoalItem:
                                            title: "Reduce daily carbon to 3 kg"
                                            progress_text: "3.4/3 kg/day"
                                            value: 85
                                        GoalItem:
                                            title: "Log 300 total habits"
                                            progress_text: "284/300 habits"
                                            value: 94
                                        GoalItem:
                                            title: "Reach Eco Score 90+"
                                            progress_text: "84/90 score"
                                            value: 93
                                        Widget:
                                        MDFillRoundFlatButton:
                                            text: "Update Goals"
                                            size_hint_x: 1
                                            text_color: 1, 1, 1, 1
                                            md_bg_color: 0.4, 0.55, 0.4, 1
                                            on_release: app.open_update_goals_popup()
                                            
                                # Hàng 4: Habit Analytics (BIỂU ĐỒ) & Preferences
                                BoxLayout:
                                    orientation: "horizontal"
                                    spacing: "15dp"
                                    size_hint_y: None
                                    height: "220dp"
                                    
                                    # Habit Analytics (Biểu đồ tròn)
                                    MDCard:
                                        size_hint_x: 0.35
                                        radius: [20]
                                        padding: "15dp"
                                        orientation: "vertical"
                                        md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                        elevation: 0
                                        BoxLayout:
                                            orientation: "horizontal"
                                            size_hint_y: None
                                            height: "30dp"
                                            MDIcon:
                                                icon: "chart-pie"
                                                theme_text_color: "Custom"
                                                text_color: 0.3, 0.6, 0.3, 1
                                                size_hint_x: None
                                                width: "30dp"
                                            MDLabel:
                                                text: "Habit Analytics"
                                                bold: True
                                                font_style: "Subtitle1"
                                        BoxLayout:
                                            orientation: "horizontal"
                                            HabitDonutChart:
                                                size_hint_x: 0.5
                                            BoxLayout:
                                                size_hint_x: 0.5
                                                orientation: "vertical"
                                                padding: "10dp"
                                                MDLabel:
                                                    text: "■ Tái chế (40%)"
                                                    font_style: "Caption"
                                                    theme_text_color: "Custom"
                                                    text_color: 0.25, 0.5, 0.25, 1
                                                MDLabel:
                                                    text: "■ Nước (30%)"
                                                    font_style: "Caption"
                                                    theme_text_color: "Custom"
                                                    text_color: 0.4, 0.65, 0.4, 1
                                                MDLabel:
                                                    text: "■ Di chuyển (20%)"
                                                    font_style: "Caption"
                                                    theme_text_color: "Custom"
                                                    text_color: 0.55, 0.75, 0.55, 1
                                                MDLabel:
                                                    text: "■ Khác (10%)"
                                                    font_style: "Caption"
                                                    theme_text_color: "Custom"
                                                    text_color: 0.7, 0.85, 0.7, 1
                                                    
                                    # Preferences
                                    MDCard:
                                        size_hint_x: 0.65
                                        radius: [20]
                                        padding: "20dp"
                                        orientation: "vertical"
                                        spacing: "10dp"
                                        md_bg_color: (0.89, 0.92, 0.88, 1) if app.theme_cls.theme_style == "Light" else (0.15, 0.15, 0.15, 1)
                                        elevation: 0
                                        BoxLayout:
                                            orientation: "horizontal"
                                            size_hint_y: None
                                            height: "30dp"
                                            MDIcon:
                                                icon: "cog-outline"
                                                theme_text_color: "Custom"
                                                text_color: 0.3, 0.6, 0.3, 1
                                                size_hint_x: None
                                                width: "30dp"
                                            MDLabel:
                                                text: "Preferences"
                                                bold: True
                                                font_style: "Subtitle1"
                                            MDRoundFlatIconButton:
                                                icon: "theme-light-dark"
                                                text: "Sáng/Tối"
                                                text_color: (0.1, 0.1, 0.1, 1) if app.theme_cls.theme_style == "Light" else (0.9, 0.9, 0.9, 1)
                                                icon_color: (0.1, 0.1, 0.1, 1) if app.theme_cls.theme_style == "Light" else (0.9, 0.9, 0.9, 1)
                                                md_bg_color: 0,0,0,0
                                                line_color: 0.7, 0.7, 0.7, 1
                                                size_hint_y: None
                                                height: "30dp"
                                                on_release: app.toggle_theme()
                                        BoxLayout:
                                            orientation: "horizontal"
                                            spacing: "15dp"
                                            PrefItem:
                                                icon: "alarm"
                                                title: "Daily reminder"
                                                value: "8:00 AM"
                                            PrefItem:
                                                icon: "ruler"
                                                title: "Units"
                                                value: "Metric (kg, L)"
                                            PrefItem:
                                                icon: "lock"
                                                title: "Privacy"
                                                value: "Friends only"
'''

class EcoTrackerApp(MDApp):
    current_photo_path = ""
    user_points = 2840
    user_streak = 12
    uploaded_hashes = []
    current_hash = ""
    
    current_eco_score = 84
    current_eco_today = 8
    
    current_habit_id_verifying = None
    current_habit_title_verifying = ""
    current_habit_xp_reward = 0
    current_habit_is_daily = True
    
    all_50_tasks = []
    
    trophy_thresholds = [500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000]
    trophy_icons = ["seed", "water", "leaf", "fire", "bike", "recycle", "earth", "star", "tree", "crown"]
    trophy_names = ["Seedling", "Water Guardian", "Carbon Cutter", "Streak Master", "Green Commuter", "Zero Waste", "Earth Hero", "Star Eco", "Tree Planter", "Eco Crown"]
    
    trophy_descriptions = [
        "Đạt tổng cộng 500 XP từ các hoạt động sống xanh.",
        "Tiết kiệm nước liên tục để đạt 1,000 XP tổng.",
        "Giảm phát thải để đạt 1,500 XP tổng.",
        "Hoạt động đều đặn để đạt 2,000 XP tổng.",
        "Di chuyển xanh thường xuyên để đạt 2,500 XP tổng.",
        "Phân loại rác tốt để đạt 3,000 XP tổng.",
        "Cống hiến vì môi trường để đạt 4,000 XP tổng.",
        "Trở thành tấm gương sáng với 5,000 XP tổng.",
        "Góp phần phủ xanh với 7,500 XP tổng.",
        "Huy hiệu tối thượng dành cho người đạt 10,000 XP."
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
        hinh_thuc = ["Tái chế", "Tiết kiệm", "Dọn dẹp", "Không sử dụng", "Quyên góp", "Tắt", "Trồng", "Giảm thiểu"]
        doi_tuong = ["chai nhựa", "túi nilon", "điện", "nước sinh hoạt", "quần áo cũ", "pin", "cây xanh", "rác hữu cơ", "đồ điện tử"]
        icons = ["recycle", "water", "flash", "leaf", "bus", "bike", "shopping", "seed"]
        
        for i in range(1, 51):
            title = f"{random.choice(hinh_thuc)} {random.choice(doi_tuong)}"
            xp = random.choice([10, 15, 20, 25]) 
            icon = random.choice(icons)
            self.all_50_tasks.append({"id": f"task_{i}", "title": title, "xp": xp, "icon": icon})
            
        daily_tasks = random.sample(self.all_50_tasks, 5)
        for i in range(5):
            habit = self.root.ids[f"habit_{i+1}"]
            task = daily_tasks[i]
            habit.title = task["title"]
            habit.xp_reward = task["xp"] * 2 
            habit.icon = task["icon"]
            
        extra_tasks = [t for t in self.all_50_tasks if t not in daily_tasks]
        for task in extra_tasks:
            item = Builder.load_string(f'''
ExtraTaskItem:
    task_id: "{task['id']}"
    title: "{task['title']}"
    icon: "{task['icon']}"
    xp_reward: {task['xp']}
''')
            self.root.ids.extra_tasks_list.add_widget(item)

        self.update_trophy_case()
        self.check_eco_path_milestones()

    def update_trophy_case(self):
        self.root.ids.trophy_grid.clear_widgets()
        unlocked_count = 0
        for i in range(10):
            is_unlocked = self.user_points >= self.trophy_thresholds[i]
            if is_unlocked: unlocked_count += 1
            
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
        content = BoxLayout(orientation='vertical', spacing='10dp', padding='20dp')
        
        color_rgba = (0.3, 0.7, 0.3, 1) if unlocked else (0.6, 0.6, 0.6, 0.5)
        icon_widget = MDLabel(
            text=f"[font=Icons][size=60]{icon}[/size][/font]", 
            markup=True, 
            halign='center', 
            theme_text_color='Custom', 
            text_color=color_rgba, 
            size_hint_y=None, 
            height='80dp'
        )
        content.add_widget(icon_widget)
        
        content.add_widget(MDLabel(text=title, font_style='H6', bold=True, halign='center', size_hint_y=None, height='30dp'))
        
        status_text = "Trạng thái: [color=#4CAF50]Đã mở khóa[/color]" if unlocked else "Trạng thái: [color=#F44336]Chưa mở khóa[/color]"
        content.add_widget(MDLabel(text=status_text, markup=True, halign='center', font_style='Caption', size_hint_y=None, height='20dp'))
        
        content.add_widget(MDLabel(text=desc, halign='center', theme_text_color='Secondary', size_hint_y=None, height='50dp'))
        
        if not unlocked:
            prog_box = BoxLayout(orientation='vertical', size_hint_y=None, height='50dp')
            prog_label = MDLabel(text=f"Tiến độ: {current_p} / {max_p} XP", font_style='Caption', halign='center')
            safe_value = min(100, max(0, (current_p/max_p)*100))
            prog_bar = MDProgressBar(value=safe_value, color=(0.4, 0.6, 0.4, 1), size_hint_y=None, height='5dp')
            prog_box.add_widget(prog_label)
            prog_box.add_widget(prog_bar)
            content.add_widget(prog_box)
        else:
            content.add_widget(Widget(size_hint_y=None, height='50dp'))
            
        btn = MDFillRoundFlatButton(text="ĐÓNG", pos_hint={'center_x': 0.5}, md_bg_color=(0.4, 0.6, 0.4, 1))
        content.add_widget(btn)
        
        self.trophy_popup = Popup(title="Chi tiết Huy hiệu", content=content, size_hint=(0.5, 0.6))
        btn.bind(on_release=lambda x: self.trophy_popup.dismiss())
        self.trophy_popup.open()

    def check_eco_path_milestones(self):
        level = (self.user_points // 1000) + 10
        next_level_xp = ((level - 9) * 1000) + 2000
        progress = int((self.user_points / next_level_xp) * 100)
        
        try:
            self.root.ids.sidebar_level_label.text = f"Lv. {level}"
            self.root.ids.sidebar_level_progress.value = progress
            self.root.ids.gami_level_title.text = f"Level {level} — Eco Ranger"
            self.root.ids.gami_xp_text.text = f"{self.user_points} / {next_level_xp} XP · {next_level_xp - self.user_points} to Level {level+1}"
            self.root.ids.gami_main_progress.value = progress
            self.root.ids.gami_streak_text.text = f"{self.user_streak} streak"
        except Exception as e: pass

    def open_edit_profile_popup(self):
        content = BoxLayout(orientation='vertical', spacing='15dp', padding='15dp')
        
        self.edit_name_input = MDTextField(
            text=self.root.ids.profile_name_label.text, 
            hint_text="Tên hiển thị",
            mode="rectangle"
        )
        current_loc = self.root.ids.profile_location_label.text.split(' · ')[0]
        self.edit_loc_input = MDTextField(
            text=current_loc, 
            hint_text="Thành phố, Quốc gia",
            mode="rectangle"
        )
        
        content.add_widget(self.edit_name_input)
        content.add_widget(self.edit_loc_input)
        
        save_btn = MDFillRoundFlatButton(
            text="LƯU THAY ĐỔI", 
            md_bg_color=(0.4, 0.6, 0.4, 1), 
            pos_hint={'center_x': 0.5},
            size_hint_x=1
        )
        save_btn.bind(on_release=self.save_profile)
        content.add_widget(save_btn)
        
        self.profile_popup = Popup(title="Chỉnh sửa Hồ sơ", content=content, size_hint=(0.5, 0.5))
        self.profile_popup.open()

    def save_profile(self, instance):
        new_name = self.edit_name_input.text
        new_loc = self.edit_loc_input.text
        if new_name.strip() != "":
            self.root.ids.profile_name_label.text = new_name
            self.root.ids.username_display.text = new_name  
        if new_loc.strip() != "":
            self.root.ids.profile_location_label.text = f"{new_loc} · Member since Jan 2025"
        self.profile_popup.dismiss()

    def open_update_goals_popup(self):
        content = BoxLayout(orientation='vertical', spacing='15dp', padding='15dp')
        
        content.add_widget(MDTextField(text="3", hint_text="Mục tiêu giảm Carbon (kg/ngày)", mode="rectangle"))
        content.add_widget(MDTextField(text="300", hint_text="Mục tiêu tổng Habits", mode="rectangle"))
        content.add_widget(MDTextField(text="90", hint_text="Mục tiêu Eco Score", mode="rectangle"))
        
        save_btn = MDFillRoundFlatButton(
            text="CẬP NHẬT", 
            md_bg_color=(0.4, 0.6, 0.4, 1), 
            pos_hint={'center_x': 0.5},
            size_hint_x=1
        )
        save_btn.bind(on_release=lambda x: self.goals_popup.dismiss())
        content.add_widget(save_btn)
        
        self.goals_popup = Popup(title="Thiết lập Mục tiêu cá nhân", content=content, size_hint=(0.5, 0.6))
        self.goals_popup.open()

    def switch_tab(self, screen_name, btn_instance):
        self.root.ids.sm.current = screen_name
        
        nav_buttons = [
            self.root.ids.nav_dashboard,
            self.root.ids.nav_gamification,
            self.root.ids.nav_social,
            self.root.ids.nav_groups,
            self.root.ids.nav_stats
        ]
        for btn in nav_buttons:
            if btn: btn.md_bg_color = [0, 0, 0, 0]
            
        if btn_instance:
            btn_instance.md_bg_color = [0.7, 0.78, 0.7, 0.6]

    def add_like(self, btn_instance, card_instance):
        current_likes = int(card_instance.like_count)
        current_likes += 1
        card_instance.like_count = str(current_likes)
        card_instance.ids.like_label.text = f"{current_likes} Thích"
        
        btn_instance.icon = "heart"
        btn_instance.text_color = (0.9, 0.2, 0.2, 1)
        btn_instance.disabled = True

    def select_daily_habit(self, habit_id, title, xp, is_daily):
        if is_daily:
            habit_widget = self.root.ids.get(habit_id)
            if habit_widget and habit_widget.checked:
                return
            
        self.current_habit_id_verifying = habit_id
        self.current_habit_title_verifying = title
        self.current_habit_xp_reward = xp
        self.current_habit_is_daily = is_daily
        
        self.root.ids.sm.current = "tab_ghi_nhan"
        self.root.ids.status_label.text = f"Nhiệm vụ: [{title}]. Cung cấp ảnh để hoàn thành!"
        self.root.ids.status_label.theme_text_color = "Custom"
        self.root.ids.status_label.text_color = (0.1, 0.5, 0.8, 1)
        self.root.ids.btn_ai_scan.disabled = True
        self.clear_current_image() 
        self.switch_tab("tab_ghi_nhan", None)

    def toggle_theme(self):
        current = self.theme_cls.theme_style
        new_style = "Dark" if current == "Light" else "Light"
        self.theme_cls.theme_style = new_style
        self.store.put('theme', style=new_style)

    def process_login(self):
        user = self.root.ids.login_user.text
        if user.strip() != "":
            self.root.ids.username_display.text = user
            self.root.ids.profile_name_label.text = user
            self.root.current = "main_app_screen"
            self.switch_tab("tab_dashboard", self.root.ids.nav_dashboard)

    def process_logout(self):
        self.root.current = "login_screen"
        self.clear_current_image()

    def update_title_label(self, current_screen_name):
        titles = {
            "tab_dashboard": ("Dashboard", "Quản lý lối sống xanh"),
            "tab_ghi_nhan": ("Xác Nhận", "Ghi nhận hành động trực tiếp"),
            "tab_gamification": ("Challenges", "Your eco journey path"),
            "tab_social": ("Community", "Mạng xã hội Xanh"),
            "tab_groups": ("Teams", "Hoạt động Nhóm"),
            "tab_stats": ("Profile", "Your eco identity")
        }
        info = titles.get(current_screen_name, ("Eco Space", ""))
        self.root.ids.title_page.text = info[0]
        self.root.ids.subtitle_page.text = info[1]

    def open_camera_popup(self):
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        header_layout = BoxLayout(size_hint_y=None, height="40dp")
        header_layout.add_widget(Widget())
        close_btn = MDIconButton(
            icon="close-circle",
            theme_text_color="Custom",
            text_color=(0.8, 0.2, 0.2, 1),
            on_release=self.close_camera_popup
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

        capture_btn = MDRaisedButton(
            text="BẤM CHỤP NGAY",
            pos_hint={"center_x": 0.5},
            md_bg_color=(0.18, 0.49, 0.2, 1),
            radius=[8, 8, 8, 8]
        )
        capture_btn.bind(on_release=self.capture_photo)
        main_layout.add_widget(capture_btn)

        self.cam_popup = Popup(
            title="Màn hình ngắm Camera trực tiếp",
            content=main_layout,
            size_hint=(0.6, 0.9),
            auto_dismiss=False
        )
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
        except: pass
        self.show_image_in_preview(output_path)

    def trigger_upload_macos(self):
        applescript = (
            'tell application "System Events"\n'
            '   activate\n'
            '   set filePath to choose file of type {"public.image"} with prompt "Chọn ảnh hành động sống xanh:"\n'
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
        except Exception as e:
            self.root.ids.status_label.text = f"Lỗi nạp file: {str(e)}"

    def show_image_in_preview(self, path):
        try:
            with open(path, "rb") as f:
                img_hash = hashlib.md5(f.read()).hexdigest()
            if img_hash in self.uploaded_hashes:
                self.root.ids.status_label.text = "CẢNH BÁO: Ảnh này đã được sử dụng trước đó!"
                self.root.ids.status_label.theme_text_color = "Custom"
                self.root.ids.status_label.text_color = (0.8, 0.2, 0.2, 1)
                os.remove(path)
                return
            self.current_hash = img_hash
        except: pass
        self.current_photo_path = path
        self.root.ids.preview_image.source = path
        self.root.ids.preview_image.reload()
        self.root.ids.status_label.text = "Ảnh đã tải lên! Bấm XÁC NHẬN để nhận điểm."
        self.root.ids.status_label.theme_text_color = "Primary"
        self.root.ids.btn_ai_scan.disabled = False
        self.root.ids.delete_image_btn.opacity = 1
        self.root.ids.delete_image_btn.disabled = False

    def clear_current_image(self):
        if self.current_photo_path and os.path.exists(self.current_photo_path):
            try: os.remove(self.current_photo_path)
            except: pass
        self.current_photo_path = ""
        self.current_hash = ""
        self.root.ids.preview_image.source = ""
        self.root.ids.status_label.text = "Hệ thống: Sẵn sàng xác nhận hình ảnh"
        self.root.ids.status_label.theme_text_color = "Primary"
        self.root.ids.btn_ai_scan.disabled = True
        self.root.ids.delete_image_btn.opacity = 0
        self.root.ids.delete_image_btn.disabled = True
        self.root.ids.btn_ai_scan.text = "XÁC NHẬN ẢNH & NHẬN ĐIỂM"
        self.root.ids.btn_ai_scan.md_bg_color = (0.1, 0.45, 0.8, 1)

    def instant_reward(self):
        # Lưu hash ảnh để chống up trùng
        if self.current_hash:
            self.uploaded_hashes.append(self.current_hash)
            
        xp_reward = self.current_habit_xp_reward if self.current_habit_id_verifying else 50
        
        # Đổi UI nút bấm
        self.root.ids.btn_ai_scan.text = "ĐANG CỘNG ĐIỂM..."
        self.root.ids.btn_ai_scan.md_bg_color = (0.4, 0.4, 0.4, 1)
        self.root.ids.btn_ai_scan.disabled = True
        
        # Luôn luôn trả về kết quả ĐẠT (GREEN)
        result = {
            "type": "GREEN", 
            "msg": f"Xác nhận thành công! (+{xp_reward} XP)", 
            "points": xp_reward, 
            "streak": 1
        }
        
        # Gọi hàm cộng điểm (để delay 0.5s cho mượt UI)
        Clock.schedule_once(lambda dt: self.apply_ai_result(result), 0.5)

    def apply_ai_result(self, result):
        old_points = self.user_points
        
        if result["points"] < 0:
            self.user_points = max(0, self.user_points + result["points"])
            self.current_eco_score = max(0, self.current_eco_score + result["points"])
            self.current_eco_today = max(0, self.current_eco_today + result["points"])
            self.user_streak = 0  
        else:
            self.user_points += result["points"]
            self.current_eco_score += result["points"]
            self.current_eco_today += result["points"]
            self.user_streak += 1
            
            if old_points < 3000 and self.user_points >= 3000:
                result["msg"] += " | 🎉 BONUS: Water Guardian Unlocked (+150 XP)!"
                self.user_points += 150
            elif old_points < 5000 and self.user_points >= 5000:
                result["msg"] += " | 🎉 BONUS: Carbon Cutter Unlocked (+200 XP)!"
                self.user_points += 200

        try:
            self.root.ids.eco_score_label.text = str(self.current_eco_score)
            self.root.ids.eco_score_today_label.text = f"+{self.current_eco_today} today"
            self.root.ids.donut_chart.value = self.current_eco_score
        except Exception as e: pass
        
        if result["type"] == "GREEN" and self.current_habit_is_daily:
            self.mark_habit_as_completed()
            
        self.update_trophy_case()
        self.check_eco_path_milestones()

        self.root.ids.status_label.text = result["msg"]
        if result["type"] == "GREEN":
            self.root.ids.status_label.theme_text_color = "Custom"
            self.root.ids.status_label.text_color = (0.15, 0.55, 0.15, 1)
            Clock.schedule_once(lambda dt: self.go_to_previous_screen(), 1.5)
        else:
            self.root.ids.status_label.theme_text_color = "Custom"
            self.root.ids.status_label.text_color = (0.8, 0.2, 0.2, 1)
            self.root.ids.btn_ai_scan.text = "QUÉT LẠI HOẶC HỦY BỎ"
            self.root.ids.btn_ai_scan.md_bg_color = (0.8, 0.3, 0.3, 1)
            self.root.ids.btn_ai_scan.disabled = False

        try:
            self.root.ids.sidebar_streak_label.text = f"{self.user_streak}-day streak"
            self.root.ids.sidebar_points_label.text = f"{self.user_points:,} XP"
        except: pass

    def mark_habit_as_completed(self):
        if not self.current_habit_id_verifying: return
        
        habit_widget = self.root.ids.get(self.current_habit_id_verifying)
        if habit_widget and not habit_widget.checked:
            habit_widget.checked = True
            
            completed_count = 0
            for i in range(1, 6):
                hw = self.root.ids.get(f"habit_{i}")
                if hw and hw.checked:
                    completed_count += 1
            
            self.root.ids.habit_progress_text.text = f"{completed_count}/5 completed"
            percentage = int((completed_count / 5) * 100)
            self.root.ids.habit_progress_bar.value = percentage
            self.root.ids.habit_percentage_text.text = f"{percentage}%"
            
    def go_to_previous_screen(self):
        if self.current_habit_is_daily:
            self.root.ids.sm.current = "tab_dashboard"
            self.switch_tab("tab_dashboard", self.root.ids.nav_dashboard)
        else:
            self.root.ids.sm.current = "tab_gamification"
            self.switch_tab("tab_gamification", self.root.ids.nav_gamification)
        self.clear_current_image()
        self.current_habit_id_verifying = None
        self.current_habit_title_verifying = ""
        self.current_habit_xp_reward = 0

if __name__ == "__main__":
    EcoTrackerApp().run()