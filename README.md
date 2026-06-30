# 🌿 Eco Tracker — Eco Space

Ứng dụng di động giúp người dùng theo dõi và xây dựng lối sống xanh hằng ngày, được xây dựng bằng **Python + Kivy/KivyMD**.

## Giới thiệu

Eco Tracker là một ứng dụng dạng gamification (chơi-mà-học) khuyến khích người dùng thực hiện các hành động bảo vệ môi trường mỗi ngày: phân loại rác, tiết kiệm nước, đi xe đạp, mang bình nước cá nhân... Người dùng xác nhận hoàn thành nhiệm vụ bằng cách chụp/tải ảnh bằng chứng, đồng thời theo dõi điểm số, level, streak, huy hiệu và thứ hạng trong nhóm bạn bè.

## Tính năng chính

- **Đăng nhập đơn giản**: nhập tên để vào ứng dụng (demo, chưa có xác thực thật).
- **Dashboard**: hiển thị Eco Score dạng biểu đồ donut, thống kê carbon/nước/năng lượng tiêu thụ, biểu đồ carbon theo tuần và Weekly Score dạng cột.
- **Nhiệm vụ hằng ngày (Daily Tasks)**: mỗi lần mở app, hệ thống random 3 nhiệm vụ từ một danh sách nhiệm vụ tổng (10 task). Bấm vào một nhiệm vụ sẽ mở trang Upload Photo để chụp/tải ảnh xác nhận; sau khi xác nhận, nhiệm vụ được đánh dấu **hoàn thành** (không cộng điểm) và **không thể làm lại**.
- **Upload ảnh**: chụp ảnh trực tiếp bằng camera hoặc chọn ảnh có sẵn (hỗ trợ macOS qua AppleScript), có kiểm tra trùng ảnh bằng hash MD5.
- **Gamification**: hệ thống Level/XP, streak ngày liên tiếp, Monthly Challenges, Trophy Case với 10 huy hiệu mở khóa theo mốc điểm.
- **Social & Feed**: danh sách bạn bè, bảng tin hoạt động eco của cộng đồng, có thể thả tim.
- **Team & Groups**: bảng xếp hạng nhóm (leaderboard) và mục tiêu chung của team.
- **Profile & Settings**: thông tin cá nhân, thống kê tổng quan, huy hiệu, mục tiêu cá nhân, tuỳ chọn (nhắc nhở, đơn vị đo, quyền riêng tư), chuyển đổi giao diện Sáng/Tối.

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3 |
| UI Framework | Kivy + KivyMD |
| Camera | `kivy.uix.camera` |
| Xử lý ảnh | OpenCV (cv2), Pillow, Numpy |
| Lưu trữ cục bộ | `kivy.storage.jsonstore` (cài đặt theme), thư mục `upload_cache/` (ảnh) |
| Layout chuẩn | Mobile dọc 360x760 |

