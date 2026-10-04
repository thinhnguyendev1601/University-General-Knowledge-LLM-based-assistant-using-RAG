# IU Study Assistant

Front-end demo theo `ke-hoach-front-end-iu-rag.md`: React + React DOM **19.2.0**, JavaScript ES modules, `React.createElement`, CSS thuần và History API. Không có bundler hoặc dependency cần cài.

## Chạy

Yêu cầu Node.js có sẵn. Tại thư mục dự án:

```sh
npm run dev
```

Mở http://localhost:3000. Nếu cổng bận: `node scripts/serve.js 3001`. Máy chủ này chỉ phục vụ file tĩnh, có SPA fallback; không phải backend của sản phẩm. React được tải từ esm.sh với phiên bản cố định, nên lần mở cần kết nối Internet. Không mở `index.html` bằng `file://`.

Chọn **Dùng thử bản demo**, hoặc nhập email bất kỳ đúng định dạng và mật khẩu **demo123**. Không dùng thông tin tài khoản thật.

## Có gì trong bản demo

- Login: validation, hiện/ẩn mật khẩu, loading, phiên lưu trên thiết bị và trở về route đã yêu cầu.
- Chat: 4 gợi ý điền vào composer, phản hồi từng phần, dừng, thử lại cùng message, nguồn đúng đoạn trích; đoạn văn, danh sách, bảng, code; sao chép và phản hồi hữu ích.
- Lịch sử: 8 hội thoại mẫu, nhóm ngày địa phương, tìm tiêu đề, mở lại, đổi tên, xác nhận xóa.
- Ticket: 6 mẫu phủ 5 trạng thái, tìm/lọc, form/chi tiết/timeline, liên kết và trích đoạn từ chat. Form có cảnh báo khi rời với thay đổi chưa gửi.
- Mobile: drawer điều hướng, nguồn dạng sheet, ticket dạng card; focus ring, labels, dialog native và reduced motion.

Chat và ticket lưu riêng theo email demo bằng localStorage, schema version 1. Không lưu mật khẩu. Đăng xuất giữ dữ liệu của tài khoản trên trình duyệt; đăng nhập lại cùng email để phục hồi. Trong **Tài khoản demo → Đặt lại dữ liệu demo** có bước xác nhận trước khi trở về dữ liệu mẫu. Dữ liệu hỏng hoặc lỗi lưu sẽ có thông báo. Stream đang chạy khi reload được phục hồi thành “Đã dừng”.

Mọi câu trả lời, tài liệu và trạng thái hỗ trợ đều mô phỏng. Chưa có backend, RAG, xác thực thật hoặc gửi ticket đến IU.

## Routes và bố cục

| Route | Desktop | Mobile |
| --- | --- | --- |
| `/login` | Giới thiệu pastel + form hai cột | Giới thiệu ngắn + form |
| `/chat`, `/chat/:id` | Sidebar 274px; vùng đọc giữa; composer cuối | Drawer; vùng đọc cuộn; composer cuối |
| `/tickets` | Danh sách dạng bảng + tìm/lọc | Danh sách dạng card |
| `/tickets/new` | Form tập trung, trích đoạn xem lại | Form một cột |
| `/tickets/:id` | Nội dung, liên kết chat, timeline | Nội dung một cột |
| ID/route không tồn tại | Thông báo + nút quay về | Tương tự |

## Kiểm tra

```sh
npm run check
npm test
node scripts/contrast.js
```

`check` kiểm tra cú pháp bằng Node; `test` chạy JavaScript assertions thuần, không có test framework. Kiểm thử router/reducer trong Node trích exports thuần từ source, bỏ imports React vì React được phân phối bằng import map ở browser; hooks được kiểm tra bằng luồng giao diện. Kết quả và giới hạn kiểm chứng ghi trong `QA.md`.

Trang preview component nội bộ: `/dev/components.html`.

Kịch bản phát triển dùng query, không đặt control kỹ thuật trong UI chính:

- `/login?scenario=login-error` hoặc `login-network`: submit credentials demo sẽ lỗi; nút dùng thử vẫn mở demo.
- `/chat?scenario=chat-error`: lỗi sau phần trả lời đầu; **Thử lại** mô phỏng lần thành công.
- `/tickets/new?scenario=ticket-error`: lỗi gửi, giữ nội dung. Đổi URL để trở về kịch bản thường.
- `/chat/id-khong-ton-tai`, `/tickets/id-khong-ton-tai`, `/duong-dan-la`: kiểm tra trạng thái không tồn tại.

## Tổ chức source

`src/app` quản lý route và store; `features` chứa màn hình; `components/ui.js` có UI dùng chung; `services/mock.js` giữ adapter async; `mocks` chứa fixture; `utils` chứa validation/persistence; `styles` chứa semantic tokens và responsive.

Khi nối dịch vụ thật: thay adapter mock và cách lưu/khôi phục phiên, giữ model UI và các trạng thái loading/error/hủy. Server thật cần xác thực, phân quyền và validation riêng; guard hiện tại chỉ phục vụ trải nghiệm demo.
