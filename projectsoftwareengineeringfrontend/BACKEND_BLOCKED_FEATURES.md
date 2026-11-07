# Tính năng chờ Backend (chưa làm)

> Cập nhật tài khoản: đăng ký giới hạn `@university.edu.vn`, kích hoạt ngay không xác minh email,
> đăng nhập, `/auth/me`, đăng xuất, đặt lại mật khẩu và cookie session đã triển
> khai thật. Hợp đồng session thay thế JWT giả ở bản ban đầu. Xem
> [tổng hợp thay đổi](../docs/08_project_changes_and_handover.md). Lịch sử server đã nối
> frontend chính theo [B4](../docs/08_project_changes_and_handover.md). API quản trị
> metadata đã có theo [tổng hợp thay đổi metadata](../docs/08_project_changes_and_handover.md); giao diện Admin vẫn là placeholder.

Danh sách các tính năng/tác vụ **hiện tại bị loại khỏi phạm vi frontend** vì phụ thuộc hoàn toàn vào backend thật (API production, database, auth service...). Theo luật trong `CLAUDE.md` mục 1 & 11, phần frontend chỉ dựng UI + gọi API qua `services/`; khi backend chưa có thì dùng `mocks/` để test UI, nhưng **không** được giả lập hay hardcode logic nghiệp vụ phía server.

| Tính năng | Nguồn trong CLAUDE.md | Lý do chờ backend | Trạng thái hiện tại |
|---|---|---|---|
| Đăng nhập thật | mục 5.1 | Đã có API và Argon2id | Hoàn thành; tài khoản active đăng nhập ngay sau đăng ký |
| Quên mật khẩu / đặt lại mật khẩu | mục 5.1 | Đã có SMTP và token dùng một lần | Hoàn thành; cần SMTP thật khi gửi đến hộp thư trường |
| Phiên đăng nhập thật | mục 5.2, 6 | PostgreSQL + cookie HttpOnly | Hoàn thành; không dùng JWT/refresh token |
| Phân quyền thực thi | mục 5.2 | Session được kiểm tra tại API | Có `require_user`/`require_admin`; lịch sử kiểm tra chủ sở hữu, admin không được vượt quyền |
| Trả lời câu hỏi từ kho dữ liệu thật (FAQ, lịch học, quy chế...) | mục 1, 5.4 | Cần backend có kho dữ liệu + engine trả lời | ✅ **Đã nối (2026-10-21):** `sendMessage` gọi `POST /api/chat/messages` của backend RAG (`api/app.py`), trả lời kèm trích dẫn. Còn thiếu UI: ô chọn trường (`getInstitutions()`), panel nguồn (`message.citations`). Xem `docs/07_api_and_wiring.md` |
| Streaming / typing indicator thật | mục 5.4 | Cần backend hỗ trợ SSE/WebSocket/polling | Chỉ có UI indicator, chưa nhận stream thật |
| Lưu hội thoại lên server (đồng bộ nhiều thiết bị) | mục 5.4 | Đã có API hội thoại/tin nhắn | Đã nối: tạo/đọc/đổi tên/xóa, reload/đăng nhập lại đọc PostgreSQL, retry giữ requestId; chưa push realtime giữa thiết bị |
| Menu **Quản lý dữ liệu** cho admin | mục 5.2 | API metadata tài liệu B1 đã có | Chỉ có placeholder, chưa build bảng/form; upload không thuộc phạm vi hiện tại |
| Xử lý lỗi mạng/server thật | mục 5.4 | Đã có hợp đồng lỗi và Retry-After | Đã nối lỗi thật, chờ Retry-After, retry cùng requestId và dùng HTTP budget từ server; không dùng nhánh mock chat trong service thật |

**Nguyên tắc khi backend chưa sẵn sàng:**
- Làm phần UI/UX đầy đủ, dùng mock tại `src/mocks/` cung cấp dữ liệu cùng kiểu (`Role`, `User`, `ChatMessage`, `ChatConversation` như mục 6) và cùng độ trễ.
- Khi backend thật ra đời, chỉ cần thay implementation trong `src/services/` — **không sửa component**.
- Mọi mục trong bảng trên được ghi nhận tại đây thay vì cố gắng "giả lập đầy đủ" logic phía server trong frontend.
