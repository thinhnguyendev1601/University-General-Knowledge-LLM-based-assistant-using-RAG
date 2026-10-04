# Kiểm chứng MVP — 04/10/2026

Hai agent kiểm tra độc lập: agent logic tạo assertions JavaScript thuần; agent UI review code theo `.agents/skills/requesting-code-review`. Agent UI không truy cập được browser trong session riêng, nên kiểm tra giao diện thực tế bên dưới do agent chính thực hiện.

## Lệnh đã chạy

- `npm run check`: PASS — cú pháp toàn bộ JavaScript trong src, scripts, dev và tests.
- `npm test`: PASS — 25/25 nhóm kiểm tra validation, route/guard, reducer, persistence/schema hỏng, user isolation, fixture, abort trước/trong/cuối stream, scenario qua navigation, retry, login/ticket failure và giữ excerpt.
- `node scripts/contrast.js`: PASS — 15 cặp semantic tokens; chữ ≥4.5:1, control/focus ≥3:1. Đây là kiểm tra cặp token, không chứng nhận WCAG toàn ứng dụng.

Không có build hoặc test framework; không cài thêm dependency.

## Luồng đã kiểm trong browser

- Submit login rỗng hiện lỗi cạnh trường và focus email; dùng thử vào chat.
- Gợi ý điền câu hỏi, gửi, phản hồi từng phần, nguồn đúng tài liệu/trang, không có link giả.
- Reload giữ phiên và chat, nguồn inline `[1]` và card có accessible name đúng.
- Tạo ticket từ chat; submit rỗng báo lỗi và focus tiêu đề; gửi hợp lệ mở chi tiết/timeline; reload giữ ticket.
- Đổi tên: focus input; lưu trả focus summary. Xóa: focus “Giữ lại”; Escape đóng và trả focus summary.
- Xóa chat đang mở về `/chat`; ticket vẫn giữ excerpt và báo chat không còn khả dụng.
- Dừng trả lời, thử lại, chuyển chat khi đang sinh: giữ “Đã dừng”, không cập nhật nhầm chat.
- `/chat?scenario=chat-error`: lỗi hiện kể cả câu hỏi đầu chuyển route, thử lại thành công.
- `/tickets/new?scenario=ticket-error`: lỗi hiện, giữ nguyên tiêu đề/mô tả.
- Form bẩn + Back: hủy giữ form; chấp nhận về list; Forward vẫn trở lại form. Điều hướng bằng nút mở confirm, nhưng công cụ điều khiển browser bị timeout tại bước xử lý confirm này; chưa xác minh được accept/cancel qua nút nội bộ bằng tự động hóa.
- Đăng xuất → dùng thử lại phục hồi lịch sử/ticket đã lưu.
- ID chat không tồn tại và route lạ hiển thị fallback có hành động quay về.
- Desktop Shift+Enter xuống dòng, Enter gửi. Mobile Enter xuống dòng; có nút gửi riêng.
- 360px: drawer, source sheet 360px, ticket card, composer dùng được; không tràn ngang toàn trang. Danh sách ticket đo thêm 390/768/1280/1440px đều có document width bằng viewport.
- Desktop thấp: 4 gợi ý và composer cùng hiển thị; chat-scroll không cuộn ở empty state 1280px.
- Console luồng chính: không ghi nhận error/warn từ ứng dụng.

## Lỗi đã sửa theo hai agent

1. Abort sát chunk cuối vẫn phát complete.
2. Dữ liệu lưu `message.error`/`ticket.course` dạng object gây React crash.
3. Sao chép block text rỗng gây spread undefined.
4. Scenario chat-error mất sau chuyển URL.
5. Dialog ưu tiên focus sai, trả focus về menu ẩn và ID tiêu đề trùng.
6. Hủy Back bằng pushState làm mất Forward stack.
7. Sheet nguồn bị max-width mặc định của dialog thu hẹp trên mobile.
8. Empty chat tự cuộn xuống cuối và textarea có scrollbar thừa sau đổi viewport.

## Chưa xác minh

- Thiết bị iOS/Android thật, bàn phím ảo, IME tiếng Việt khi composition và safe-area thực tế.
- Screen reader thực, zoom browser 200%, các browser ngoài Chromium.
- Clipboard thành công/thất bại trên mọi browser; code có catch và toast nhưng chưa chạy đầy đủ ở browser.
- Reset dữ liệu qua dialog, thiếu kết nối CDN thực và quota localStorage thực trong browser; các trường hợp schema/storage denial/quota được kiểm bằng assertions.
- Chưa thực hiện audit WCAG toàn diện. Native dialog và AX tree được kiểm, nhưng không thay thế kiểm thử với người dùng công nghệ hỗ trợ.

## Kiểm tra thủ công bổ sung

1. Mở `/dev/components.html`, duyệt bằng Tab/Shift+Tab, kiểm focus, hover, disabled, error.
2. Dùng điện thoại thật mở bản demo, thử composer khi bàn phím hiện; Enter/Shift+Enter và IME.
3. Dùng screen reader đọc login, trạng thái chat, citation và ticket; thử zoom 200%.
4. Thử reset trong tài khoản, login-error/login-network và clipboard; kiểm form bẩn với điều hướng nội bộ, reload và đóng tab.
