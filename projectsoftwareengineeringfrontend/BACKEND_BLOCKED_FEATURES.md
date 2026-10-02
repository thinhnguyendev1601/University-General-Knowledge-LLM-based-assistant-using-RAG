# Tính năng chờ Backend (chưa làm)

Danh sách các tính năng/tác vụ **hiện tại bị loại khỏi phạm vi frontend** vì phụ thuộc hoàn toàn vào backend thật (API production, database, auth service...). Theo luật trong `CLAUDE.md` mục 1 & 11, phần frontend chỉ dựng UI + gọi API qua `services/`; khi backend chưa có thì dùng `mocks/` để test UI, nhưng **không** được giả lập hay hardcode logic nghiệp vụ phía server.

| Tính năng | Nguồn trong CLAUDE.md | Lý do chờ backend | Trạng thái hiện tại |
|---|---|---|---|
| Đăng nhập thật (xác thực email + mật khẩu) | mục 5.1 | Cần endpoint `POST /api/auth/login` + xác thực hash mật khẩu | Chỉ có mock, validate form hoạt động, gọi API giả lập |
| Quên mật khẩu / đặt lại mật khẩu | mục 5.1 | Cần email service + flow reset password phía server | Chỉ có giao diện nút, chưa có logic |
| Session/token thật (JWT, refresh token) | mục 5.2, 6 | Cần backend cấp & validate token, cần endpoint `POST /api/auth/refresh` | Auth store hoạt động với token giả. `httpClient` đã có sẵn chỗ nối refresh (bắt 401 → gọi `refreshAccessToken()` → gửi lại request 1 lần), nhưng `refreshAccessToken()` trả `null` vì chưa có endpoint |
| Phân quyền thực thi (role `admin`/`user`) | mục 5.2 | Frontend chỉ ẩn/hiện UI, không phải biện pháp bảo mật | Có `RequireAuth`/`RequireRole` UX-level, backend phải tự chặn API riêng |
| Trả lời câu hỏi từ kho dữ liệu thật (FAQ, lịch học, quy chế...) | mục 1, 5.4 | Cần backend có kho dữ liệu + engine trả lời | Chat dùng mock trả lời, không có logic tra cứu thật |
| Streaming / typing indicator thật | mục 5.4 | Cần backend hỗ trợ SSE/WebSocket/polling | Chỉ có UI indicator, chưa nhận stream thật |
| Lưu hội thoại lên server (đồng bộ nhiều thiết bị) | mục 5.4 | Cần endpoint `GET/POST/DELETE /api/chat/conversations` | Lịch sử lưu localStorage, không đồng bộ backend |
| Menu **Quản lý dữ liệu** cho admin | mục 5.2 | Cần CRUD API cho nội dung (FAQ, lịch học...) quản trị | Chỉ có placeholder, chưa build form/quản trị |
| Xử lý lỗi mạng/server thật | mục 5.4 | Cần endpoint lỗi trả về hợp đồng chuẩn (mã lỗi, message) | Nút "Thử lại" hoạt động với error giả lập. Bật `VITE_MOCK_ERROR_RATE` trong `.env.local` để mock chat ném lỗi và test luồng này |

**Nguyên tắc khi backend chưa sẵn sàng:**
- Làm phần UI/UX đầy đủ, dùng mock tại `src/mocks/` cung cấp dữ liệu cùng kiểu (`Role`, `User`, `ChatMessage`, `ChatConversation` như mục 6) và cùng độ trễ.
- Khi backend thật ra đời, chỉ cần thay implementation trong `src/services/` — **không sửa component**.
- Mọi mục trong bảng trên được ghi nhận tại đây thay vì cố gắng "giả lập đầy đủ" logic phía server trong frontend.
