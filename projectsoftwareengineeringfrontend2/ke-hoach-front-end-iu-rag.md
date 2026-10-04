# Kế hoạch front-end — IU Study Assistant

## 1. Mục tiêu và giả định

Xây dựng giao diện trợ lý học tập dành cho sinh viên IU, giúp người dùng đặt câu hỏi, xem lại hội thoại và gửi ticket khi cần hỗ trợ thêm. Tên **IU Study Assistant** là tên làm việc, có thể đổi sau.

Kế hoạch này chỉ bao gồm front-end. Bản đầu chạy với dữ liệu giả và các thao tác mô phỏng; không triển khai xác thực thật, máy chủ, truy xuất RAG, cơ sở dữ liệu, xử lý tài liệu hay hệ thống tiếp nhận ticket thật.

Các giả định ban đầu:

- Người dùng chính là sinh viên; chưa xây dựng giao diện quản trị hoặc giao diện nhân viên xử lý ticket.
- Giao diện mặc định bằng tiếng Việt; tên môn học và nội dung tài liệu có thể bằng tiếng Anh.
- Thiết kế ưu tiên desktop nhưng sử dụng đầy đủ trên điện thoại.
- Logo, màu nhận diện, miền email và quy định xác thực của IU cần được xác nhận trước khi dùng như thông tin chính thức.
- Ảnh Studocu là tham khảo về màu sắc, khoảng trắng và thẻ nội dung. Ảnh thứ hai là giao diện Codex, được tham khảo về sidebar và vùng nhập hội thoại; định hướng hội thoại ChatGPT dựa trên yêu cầu của người dùng.

## 2. Phạm vi sản phẩm

| Hạng mục | MVP front-end | Để sau MVP |
| --- | --- | --- |
| Đăng nhập | Form email/mật khẩu, validation, hiện/ẩn mật khẩu, trạng thái chờ/lỗi, phiên demo | Đăng ký, khôi phục mật khẩu hoàn chỉnh, SSO sau khi có yêu cầu |
| Chatbot | Chat mới, nhập câu hỏi, câu trả lời giả lập theo luồng, nguồn tham khảo, dừng sinh, thử lại | Đính kèm tài liệu, tìm kiếm nhiều môn, cá nhân hóa sâu |
| Lịch sử chat | Danh sách, tìm kiếm tiêu đề, mở lại, đổi tên, xóa | Ghim, lưu trữ, xuất hội thoại |
| Ticket | Tạo ticket, danh sách ticket của tôi, xem chi tiết và trạng thái mô phỏng | Trao đổi bổ sung, tệp đính kèm, giao diện xử lý ticket |
| Giao diện chung | Responsive, keyboard navigation, trạng thái rỗng/chờ/lỗi | Dark mode, đa ngôn ngữ đầy đủ |

**Điểm kết thúc MVP:** người dùng có thể đăng nhập demo → hỏi một câu → đọc câu trả lời và nguồn → mở lại chat → tạo ticket liên quan → xem ticket sau khi tải lại trang.

## 3. Định hướng thiết kế: Studocu × ChatGPT

### 3.1. Nguyên tắc kết hợp

- Từ Studocu: không khí học tập tích cực, accent xanh dương, thẻ gợi ý và thẻ tài liệu bo góc, nền pastel nhẹ.
- Từ ChatGPT: sidebar lịch sử, vùng hội thoại tập trung, ô nhập cố định ở cuối, ít yếu tố gây phân tâm.
- Phần đăng nhập có thể giàu hình ảnh hơn; màn hình chat cần tiết chế để nội dung học tập là trọng tâm.
- Không sao chép logo hoặc tuyên bố thương hiệu của Studocu/ChatGPT. Xây dựng nhận diện riêng cho dự án IU.
- Không đưa các khối marketing dài của trang Studocu vào vùng làm việc chatbot.

### 3.2. Bảng màu nền tảng — light theme cho MVP

Hướng màu: **xanh dương học thuật + nền trắng/xám nhẹ + điểm nhấn pastel**. Đây là bảng màu riêng của dự án, chưa phải bộ nhận diện chính thức của IU. Ước lượng phân bố diện tích: 80% nền trung tính, 15% nền pastel và 5% màu nhấn mạnh. Xanh dương dẫn dắt thao tác; xanh lá, tím và vàng chỉ xuất hiện theo ngữ cảnh.

| Token | Giá trị khởi điểm | Mục đích |
| --- | --- | --- |
| Primary | `#2563EB` | Nút chính, liên kết, trạng thái được chọn |
| Page background | `#F8FAFC` | Nền ứng dụng |
| Surface | `#FFFFFF` | Thẻ, modal, composer |
| Main text | `#0F172A` | Nội dung chính |
| Secondary text | `#475569` | Metadata và mô tả |
| Border | `#E2E8F0` | Phân tách khu vực |
| Pastel blue | `#EFF6FF` | Thẻ môn học/gợi ý |
| Pastel green | `#F0FDF4` | Khối hỗ trợ hoặc trạng thái tích cực |
| Error | `#B91C1C` | Lỗi form và thao tác |
| Radius | 12–16 px; pill cho chip | Bo góc có hệ thống |
| Spacing | 4, 8, 12, 16, 24, 32, 48 px | Khoảng cách nhất quán |

Dùng font sans-serif hỗ trợ tiếng Việt, body khoảng 16 px, line-height 1.5–1.7. Kiểm tra tương phản ở từng tổ hợp thực tế; màu pastel chủ yếu làm nền, không dùng làm chữ nhỏ.

#### 3.2.1. Thang màu gốc

| Nhóm | Nhạt nhất | Nhạt | Trung bình | Chính | Đậm | Rất đậm |
| --- | --- | --- | --- | --- | --- | --- |
| Blue | `#EFF6FF` | `#DBEAFE` | `#93C5FD` | `#2563EB` | `#1D4ED8` | `#1E40AF` |
| Slate | `#F8FAFC` | `#F1F5F9` | `#CBD5E1` | `#64748B` | `#475569` | `#0F172A` |
| Green | `#F0FDF4` | `#DCFCE7` | `#86EFAC` | `#16A34A` | `#15803D` | `#166534` |
| Amber | `#FFFBEB` | `#FEF3C7` | `#FCD34D` | `#D97706` | `#B45309` | `#92400E` |
| Red | `#FEF2F2` | `#FEE2E2` | `#FCA5A5` | `#DC2626` | `#B91C1C` | `#991B1B` |
| Violet | `#F5F3FF` | `#EDE9FE` | `#C4B5FD` | `#7C3AED` | `#6D28D9` | `#5B21B6` |

Thang màu gốc phục vụ xây token. Component sử dụng token theo chức năng bên dưới để tránh chọn màu tùy ý ở từng màn hình.

#### 3.2.2. Semantic tokens

| Token CSS | Giá trị | Quy tắc sử dụng |
| --- | --- | --- |
| `--bg-page` | `#F8FAFC` | Nền login và trang ticket |
| `--bg-surface` | `#FFFFFF` | Hội thoại, form, modal, panel nguồn |
| `--bg-sidebar` | `#F1F5F9` | Sidebar và drawer mobile |
| `--bg-hover` | `#E2E8F0` | Hover hàng lịch sử và nút ghost |
| `--bg-selected` | `#DBEAFE` | Hội thoại/menu đang được chọn |
| `--text-primary` | `#0F172A` | Tiêu đề, tin nhắn, nội dung form |
| `--text-secondary` | `#475569` | Mô tả, metadata |
| `--text-muted` | `#64748B` | Placeholder và thông tin phụ trên nền trắng |
| `--text-on-primary` | `#FFFFFF` | Chữ/icon trên nút xanh đậm |
| `--text-link` | `#1D4ED8` | Link và citation; có gạch chân trong nội dung dài |
| `--border-subtle` | `#E2E8F0` | Viền trang trí, divider |
| `--border-control` | `#64748B` | Viền input/select cần nhận diện rõ |
| `--focus-ring` | `#2563EB` | Viền focus 2 px, offset 2 px |
| `--action-primary` | `#2563EB` | Login, gửi câu hỏi, gửi ticket |
| `--action-primary-hover` | `#1D4ED8` | Hover nút chính |
| `--action-primary-active` | `#1E40AF` | Khi nhấn nút chính |
| `--action-danger` | `#B91C1C` | Xác nhận xóa |
| `--action-danger-hover` | `#991B1B` | Hover hành động xóa |
| `--bg-disabled` | `#E2E8F0` | Nút/trường bị vô hiệu hóa |
| `--text-disabled` | `#475569` | Nhãn disabled, kèm trạng thái vô hiệu hóa thật |
| `--overlay` | `rgba(15, 23, 42, 0.40)` | Lớp phủ phía sau modal/drawer |
| `--shadow-card` | `0 4px 16px rgba(15, 23, 42, 0.06)` | Card nổi nhẹ |
| `--shadow-dialog` | `0 16px 48px rgba(15, 23, 42, 0.16)` | Dialog và panel nổi |

`--border-subtle` chỉ phân tách trang trí; dùng `--border-control` nếu viền là dấu hiệu nhận diện trường nhập. Không giảm opacity toàn component disabled vì có thể làm chữ khó đọc.

#### 3.2.3. Màu trạng thái và ticket

| Ngữ nghĩa / trạng thái | Nền | Chữ và icon | Viền | Biểu đạt bổ sung |
| --- | --- | --- | --- | --- |
| Thông tin / Đã gửi | `#EFF6FF` | `#1E40AF` | `#93C5FD` | Icon thông tin + nhãn |
| Đang xử lý | `#F5F3FF` | `#5B21B6` | `#C4B5FD` | Icon tiến trình + nhãn |
| Cảnh báo / Cần bổ sung | `#FFFBEB` | `#92400E` | `#FCD34D` | Icon cảnh báo + hướng dẫn |
| Thành công / Đã giải quyết | `#F0FDF4` | `#166534` | `#86EFAC` | Icon check + nhãn |
| Đã đóng | `#F1F5F9` | `#475569` | `#CBD5E1` | Icon đóng + nhãn |
| Lỗi form / gửi thất bại | `#FEF2F2` | `#991B1B` | `#B91C1C` | Icon lỗi + nội dung lỗi |

Màu đỏ biểu thị lỗi hoặc thao tác xóa, không dùng cho trạng thái “Đã đóng”. Viền nhạt của badge chỉ để trang trí; nội dung chữ và icon phải truyền đạt trạng thái độc lập với màu.

#### 3.2.4. Áp dụng theo màn hình

| Khu vực | Nền | Chữ / điểm nhấn | Chi tiết |
| --- | --- | --- | --- |
| Login — toàn trang | `#F8FAFC` | `#0F172A` | Form trắng; CTA xanh `#2563EB` |
| Login — phần giới thiệu | Gradient `#EFF6FF` → `#F5F3FF` | `#0F172A`, accent `#1D4ED8` | Chữ trên vùng sáng; gradient chỉ trang trí |
| Sidebar | `#F1F5F9` | `#475569` | Selected: nền `#DBEAFE`, chữ `#1E40AF` |
| Chat — vùng đọc | `#FFFFFF` | `#0F172A` | Giảm màu trang trí ở câu trả lời dài |
| Tin nhắn sinh viên | `#EFF6FF` | `#0F172A` | Bubble xanh nhạt, tên vai trò rõ |
| Tin nhắn trợ lý | `#FFFFFF` | `#0F172A` | Avatar xanh; nội dung không nhuộm xanh toàn khối |
| Composer | `#FFFFFF` | `#0F172A` | Viền `#64748B`, focus `#2563EB`, gửi xanh đậm |
| Citation | `#DBEAFE` | `#1E40AF` | Hover nền `#BFDBFE`, vẫn giữ số nguồn |
| Panel nguồn | `#FFFFFF` | `#0F172A` | Đoạn trích nền `#F8FAFC`, link `#1D4ED8` |
| Ticket list | `#F8FAFC` | `#0F172A` | Hàng/card trắng, hover `#F1F5F9` |
| Ticket form/detail | `#FFFFFF` | `#0F172A` | Lỗi trường dùng red; timeline dùng badge trạng thái |
| Code block | `#0F172A` | `#F1F5F9` | Header `#1E293B`; nút copy có focus sáng |

Thẻ gợi ý ở chat mới có bốn biến thể: xanh `#EFF6FF`/icon `#1E40AF`, xanh lá `#F0FDF4`/icon `#166534`, tím `#F5F3FF`/icon `#5B21B6`, vàng `#FFFBEB`/icon `#92400E`. Tiêu đề dùng `#0F172A`, mô tả dùng `#475569`; không dùng mỗi màu để phân loại nội dung.

#### 3.2.5. Trạng thái tương tác của component

| Component | Default | Hover | Active / selected | Focus / lỗi |
| --- | --- | --- | --- | --- |
| Primary button | Nền `#2563EB`, chữ trắng | Nền `#1D4ED8` | Nền `#1E40AF` | Ring xanh với offset trắng |
| Secondary button | Nền trắng, chữ `#334155`, viền `#64748B` | Nền `#F1F5F9` | Nền `#E2E8F0` | Ring `#2563EB` |
| Ghost/icon button | Trong suốt, icon `#475569` | Nền `#E2E8F0` | Nền `#DBEAFE`, icon `#1E40AF` | Ring xanh |
| Input/select | Nền trắng, chữ `#0F172A`, viền `#64748B` | Viền `#475569` | Giữ nền trắng khi có dữ liệu | Focus viền/ring xanh; lỗi viền `#B91C1C` |
| History row | Nền sidebar, chữ `#475569` | Nền `#E2E8F0` | Nền `#DBEAFE`, chữ `#1E40AF` | Ring xanh; selected kèm dấu chỉ thị |
| Destructive button | Nền `#B91C1C`, chữ trắng | Nền `#991B1B` | Nền `#7F1D1D` | Ring `#B91C1C` |

- Loading: giữ màu nút, thêm spinner cùng màu nhãn và ngăn gửi lặp.
- Disabled: nền `#E2E8F0`, chữ `#475569`, không áp dụng hover, dùng thuộc tính disabled thích hợp.
- Trường vừa lỗi vừa focus: giữ viền đỏ và hiển thị focus ring xanh phía ngoài, đồng thời giữ thông báo lỗi.
- Focus trên code block tối: dùng ring `#93C5FD` để nhận diện rõ trên nền tối.

#### 3.2.6. Quy tắc triển khai màu trong React

Khai báo màu tại `src/styles/tokens.css`, import một lần ở entry của ứng dụng. React component sử dụng class theo biến thể như `primary`, `secondary`, `danger`; stylesheet ánh xạ các biến thể tới CSS custom properties.

```css
:root {
  --bg-page: #f8fafc;
  --bg-surface: #ffffff;
  --bg-sidebar: #f1f5f9;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --action-primary: #2563eb;
  --action-primary-hover: #1d4ed8;
  --action-primary-active: #1e40af;
  --text-on-primary: #ffffff;
  --focus-ring: #2563eb;
}

.button-primary {
  background: var(--action-primary);
  color: var(--text-on-primary);
}
.button-primary:hover:not(:disabled) {
  background: var(--action-primary-hover);
}
.button-primary:active:not(:disabled) {
  background: var(--action-primary-active);
}
.button-primary:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
```

Đây là đoạn minh họa trong kế hoạch; khi triển khai cần khai báo đầy đủ token, trạng thái disabled và các biến thể. Không hardcode hex trong JSX. Nếu thêm dark mode sau MVP, ghi đè semantic tokens theo theme và kiểm tra lại từng cặp màu.

#### 3.2.7. Checklist kiểm tra bảng màu

- [ ] Chữ thường đạt tương phản tối thiểu 4.5:1; chữ lớn đạt 3:1.
- [ ] Viền nhận diện control, icon chức năng và dấu hiệu trạng thái cần thiết đạt 3:1 với nền liên quan.
- [ ] Kiểm tra đủ default, hover, active, focus, error và disabled; kiểm tra lại khi có opacity/overlay.
- [ ] `#64748B` chỉ dùng cho chữ nhỏ trên nền trắng sau kiểm tra; trên nền pastel/sidebar ưu tiên `#475569`.
- [ ] Trạng thái ticket có nhãn và icon, vẫn hiểu được khi xem grayscale.
- [ ] Dùng một trang component preview nội bộ để duyệt bảng màu trước khi áp dụng toàn bộ màn hình.
- [ ] Đo tương phản bằng công cụ hoặc script khi triển khai; bảng màu này chưa phải chứng nhận accessibility cho giao diện hoàn chỉnh.

### 3.3. Bố cục màn hình chat

```text
┌──────────────────┬──────────────────────────────────────────┐
│ IU Study         │ Tiêu đề hội thoại          Hỗ trợ / Profile│
│ + Chat mới       ├──────────────────────────────────────────┤
│ Tìm hội thoại    │                                          │
│                  │   Câu hỏi của sinh viên                  │
│ Hôm nay          │   Câu trả lời + nguồn tham khảo          │
│ • Calculus 1     │                                          │
│ • Đăng ký môn    │   [Sao chép] [Hữu ích] [Tạo ticket]      │
│                  │                                          │
│ Ticket của tôi   ├──────────────────────────────────────────┤
│ Tài khoản        │ [Nhập câu hỏi...                  ] [Gửi] │
└──────────────────┴──────────────────────────────────────────┘
```

- Sidebar desktop khoảng 260–280 px, có thể thu gọn.
- Vùng đọc giới hạn khoảng 760–860 px để câu trả lời dài dễ theo dõi.
- Composer nằm cuối vùng chat; chỉ danh sách tin nhắn cuộn khi phù hợp.
- Trên mobile, sidebar chuyển thành drawer; nguồn mở bằng sheet toàn chiều rộng.

## 4. Kiến trúc thông tin và routes

| Route dự kiến | Nội dung | Điều kiện |
| --- | --- | --- |
| `/login` | Đăng nhập demo | Công khai |
| `/chat` | Chat mới và gợi ý câu hỏi | Có phiên demo |
| `/chat/:conversationId` | Hội thoại đã lưu | Có phiên demo |
| `/tickets` | Danh sách ticket của tôi | Có phiên demo |
| `/tickets/new` | Tạo ticket | Có phiên demo |
| `/tickets/:ticketId` | Chi tiết ticket | Có phiên demo |
| Route không tồn tại | Trang 404 và điều hướng về chat | Theo phiên hiện tại |

Route guard chỉ điều khiển trải nghiệm demo; không phải cơ chế bảo mật. Khi mở ID không tồn tại, hiển thị thông báo rõ ràng và đường quay lại.

## 5. Đặc tả từng màn hình

### 5.1. Đăng nhập

Desktop chia hai cột: một bên giới thiệu ngắn về trợ lý học tập với thẻ pastel; một bên chứa form. Mobile chỉ giữ form và phần giới thiệu ngắn.

**Thành phần:** tên sản phẩm, email, mật khẩu, nút hiện/ẩn mật khẩu, nút đăng nhập, nút “Dùng thử bản demo”, thông báo lỗi.

**Hành vi:**

1. Kiểm tra trường bắt buộc và định dạng email; không tự đặt quy tắc miền email IU khi chưa được xác nhận.
2. Hiển thị lỗi ngay dưới trường, đưa focus về trường lỗi đầu tiên khi submit.
3. Trong lúc chờ, khóa submit để tránh gửi lặp nhưng giữ thông tin đã nhập.
4. Mô phỏng thành công, thông tin không hợp lệ và lỗi kết nối bằng kịch bản demo có kiểm soát.
5. Sau khi đăng nhập, quay về route người dùng định mở hoặc `/chat`.
6. Đăng xuất kết thúc phiên demo; dữ liệu demo được phân vùng theo người dùng hoặc xóa theo quy ước đã công bố.

Không lưu mật khẩu. Form phải ghi rõ đây là bản demo và không yêu cầu dùng thông tin tài khoản thật. Chỉ thêm nút SSO/quên mật khẩu khi có hành vi hoàn chỉnh; không để nút chết.

### 5.2. Chat mới

- Lời chào ngắn: “Bạn muốn tìm hiểu điều gì hôm nay?”
- Bốn thẻ gợi ý: giải thích khái niệm, hướng dẫn bài tập, tìm nội dung trong tài liệu, hỏi thông tin học tập.
- Click gợi ý điền câu hỏi vào composer để người dùng kiểm tra trước khi gửi.
- Ví dụ gợi ý: “Giải thích đạo hàm bằng một ví dụ đơn giản.”
- Không hiển thị tên môn học hoặc quy định IU như dữ liệu chính thức nếu chỉ là mock.

### 5.3. Hội thoại chatbot

**Composer:** textarea tự tăng chiều cao có giới hạn, nút gửi, nút dừng khi đang sinh. Enter gửi trên desktop, Shift+Enter xuống dòng; tránh submit trong quá trình IME composition. Trên mobile ưu tiên nút gửi rõ ràng.

**Message:** phân biệt người dùng và trợ lý bằng bố cục, nhãn và màu nhẹ. Nội dung mẫu có cấu trúc gồm đoạn văn, danh sách, bảng và code block, được render trực tiếp bằng React elements; nội dung toán học là phần mở rộng ưu tiên nếu bộ câu hỏi mục tiêu yêu cầu.

**Trạng thái cần thiết:** chờ phản hồi, đang nhận từng phần, hoàn tất, bị dừng, lỗi kết nối, không có nguồn, không đủ thông tin và hội thoại rỗng.

**Hành vi:**

- Bỏ qua tin nhắn chỉ có khoảng trắng; giới hạn độ dài dự kiến 4.000 ký tự và hiển thị lỗi có thể điều chỉnh sau.
- Tin nhắn đầu tiên tạo hội thoại và tiêu đề ngắn từ nội dung câu hỏi.
- Tự cuộn khi người dùng đang gần cuối; khi đang đọc phần cũ, hiện nút “Xuống tin nhắn mới”.
- Dừng sinh giữ phần nội dung đã nhận và ghi trạng thái “Đã dừng”.
- Thử lại cập nhật lần trả lời bị lỗi, tránh tạo hai bản trả lời không rõ quan hệ.
- Sao chép chỉ lấy nội dung trả lời; có toast xác nhận và xử lý lỗi clipboard.
- Nút hữu ích/chưa hữu ích lưu phản hồi demo và thể hiện trạng thái đã chọn.
- “Tạo ticket” dẫn tới form, gắn ID hội thoại và chỉ trích đoạn được chọn để người dùng xem lại.

### 5.4. Giao diện nguồn tham khảo cho RAG

Đây là phần trình bày dữ liệu RAG giả lập, không thực hiện retrieval.

- Cuối câu trả lời hiển thị thẻ nguồn gồm tên tài liệu, môn học nếu có, trang/mục nếu có.
- Nếu câu trả lời có ký hiệu `[1]`, `[2]`, mỗi ký hiệu phải mở đúng nguồn tương ứng.
- Mở nguồn trong panel desktop hoặc sheet mobile: tên, đoạn trích, trang và liên kết xem tài liệu nếu được cung cấp.
- Tài liệu không có URL vẫn xem được đoạn trích; không tạo liên kết giả.
- Phân biệt nội dung “Có nguồn tham khảo” với “Câu trả lời tổng quát, chưa có nguồn”.
- Không dùng phần trăm độ tin cậy khi không có định nghĩa và dữ liệu hợp lệ.
- Các nguồn demo ghi rõ “Tài liệu mẫu”; không tạo cảm giác đây là xác nhận chính thức của IU.

### 5.5. Lịch sử chat

- Nhóm theo “Hôm nay”, “7 ngày gần đây”, “Cũ hơn” theo ngày địa phương.
- Tìm kiếm tiêu đề không phân biệt hoa thường; nêu rõ phạm vi tìm kiếm chỉ là tiêu đề trong MVP.
- Hội thoại đang mở có trạng thái selected rõ ràng.
- Menu từng hội thoại: đổi tên và xóa; thao tác dùng được bằng bàn phím.
- Đổi tên: 1–80 ký tự sau khi trim; Enter xác nhận, Escape hủy.
- Xóa cần xác nhận; nếu xóa hội thoại đang mở thì chuyển về `/chat`.
- Khi không có kết quả, giữ từ khóa và cung cấp hành động xóa bộ lọc.
- Nếu ticket tham chiếu chat đã xóa, ticket vẫn giữ trích đoạn và báo hội thoại không còn khả dụng.

### 5.6. Tạo ticket

**Trường dữ liệu:**

| Trường | Quy tắc front-end đề xuất |
| --- | --- |
| Tiêu đề | Bắt buộc, 5–120 ký tự sau trim |
| Danh mục | Bắt buộc: nội dung trả lời, nguồn tài liệu, vấn đề giao diện, khác |
| Môn học | Không bắt buộc; chọn từ danh sách mẫu hoặc nhập tên |
| Mô tả | Bắt buộc, 20–3.000 ký tự sau trim |
| Liên kết hội thoại | Không bắt buộc; tự điền khi tạo từ chat |
| Trích đoạn | Có thể xem và bỏ trước khi gửi |

**Luồng:** mở form → nhập nội dung → kiểm tra lỗi → gửi mô phỏng → thông báo thành công → mở ticket mới.

- Trong lúc gửi, chặn submit trùng và hiển thị trạng thái chờ.
- Lỗi gửi giữ nguyên dữ liệu để thử lại.
- Rời form khi có thay đổi chưa gửi cần cảnh báo trong điều hướng nội bộ; tải lại/đóng tab dùng cơ chế cảnh báo trình duyệt khi được hỗ trợ.
- Hiển thị rõ ticket chỉ được lưu trên thiết bị trong bản demo và chưa gửi tới nhân viên IU.
- Chưa có upload tệp trong MVP; tránh hiển thị nút đính kèm không hoạt động.

### 5.7. Danh sách và chi tiết ticket

**Danh sách:** mã, tiêu đề, danh mục, trạng thái, ngày tạo; tìm tiêu đề/mã, lọc trạng thái, mặc định mới nhất trước. Desktop dùng bảng, mobile dùng card.

**Trạng thái mô phỏng:** đã gửi, đang xử lý, cần bổ sung, đã giải quyết, đã đóng. Người dùng không tự đổi trạng thái ở MVP; các fixture mô tả các tình huống khác nhau.

**Chi tiết:** thông tin ticket, mô tả, trích đoạn chat, liên kết hội thoại còn tồn tại, timeline mẫu. Nếu cần bổ sung, hiển thị giải thích trạng thái; tính năng gửi bổ sung chỉ được thêm ở giai đoạn sau.

Không ghi thời gian phản hồi cam kết khi chưa có quy trình hỗ trợ thực tế.

## 6. Hướng tổ chức kỹ thuật front-end

**Chốt React là thư viện front-end duy nhất**, kết hợp JavaScript thuần, HTML/CSS tiêu chuẩn và kiến trúc SPA. Functional components và hooks quản lý UI; History API quản lý điều hướng. Dùng CSS thuần và CSS custom properties cho bảng màu mục 3.2. Không sử dụng TypeScript hoặc thư viện bổ sung.

Phân công trách nhiệm trong ứng dụng React:

- `AppShell` giữ bố cục chung; mỗi route tải màn hình tương ứng.
- Custom hooks như `useConversation`, `useChatReply`, `useTickets` kết nối state với mock adapter.
- Form giữ state nhập liệu cục bộ; phiên demo và dữ liệu chia sẻ đi qua provider/store có phạm vi rõ ràng.
- Effect có cleanup để hủy luồng phản hồi hoặc listener khi component unmount/chuyển hội thoại.
- Token màu nằm trong stylesheet dùng chung; props điều khiển biến thể component thay vì truyền mã màu trực tiếp.

Các nguyên tắc:

- Tách UI, nghiệp vụ giao diện và lớp truy cập dữ liệu.
- Giai đoạn đầu mọi dữ liệu đi qua adapter mock bất đồng bộ để có loading/error thật trong UI.
- Sau này thay adapter khi có dịch vụ thật; không đưa thiết kế máy chủ vào phạm vi hiện tại.
- State cục bộ cho form/menu/drawer; state dùng chung cho phiên demo, chat và ticket.
- Lưu dữ liệu mẫu bằng localStorage với schema version; phục hồi có kiểm tra và có nút reset dữ liệu demo.
- Không lưu mật khẩu hoặc giả định localStorage là nơi lưu token an toàn.
- Render nội dung có cấu trúc bằng React elements, không chèn HTML tùy ý; kiểm tra URL của liên kết nguồn.

```text
src/
  app/                # Điều hướng History API, providers, app shell
  features/
    auth/             # Login và phiên demo
    chat/             # Composer, messages, streaming mock
    history/          # Tìm kiếm, đổi tên, xóa chat
    tickets/          # Form, list, detail
    sources/          # Citation và panel nguồn
  components/ui/      # Button, field, dialog, toast, drawer
  services/           # Interface và mock adapters
  mocks/              # Fixture và kịch bản phản hồi
  styles/             # Tokens và style chung
  models/             # Mô hình dữ liệu và kiểm tra cấu trúc bằng JavaScript
  utils/              # Ngày, validation, persistence
```

### 6.1. Mô hình dữ liệu giao diện

| Model | Trường chính |
| --- | --- |
| DemoUser | id, displayName, email |
| Conversation | id, title, createdAt, updatedAt, messages |
| Message | id, role, content, status, createdAt, citations, feedback |
| Citation | id, documentTitle, excerpt, page?, section?, url?, course? |
| Ticket | id, title, category, course?, description, status, createdAt, conversationId?, selectedExcerpt?, timeline |

### 6.2. Interface ở lớp front-end

- `authService.login()` / `logout()` / `getSession()`.
- `chatService.list()` / `get()` / `create()` / `rename()` / `remove()`.
- `chatService.reply()` nhận tín hiệu hủy và cung cấp các phần nội dung giả lập.
- `ticketService.list()` / `get()` / `create()`.

Các interface trên là ranh giới nội bộ của front-end, không phải đặc tả endpoint. Quy định rõ thao tác hủy khi chuyển chat, tránh đưa phản hồi đang chạy vào nhầm hội thoại.

### 6.3. Bảng công nghệ — chỉ sử dụng React

**Quyết định:** React là thư viện duy nhất của front-end. Dùng JavaScript thuần, HTML và CSS tiêu chuẩn cùng API có sẵn trong trình duyệt. React DOM là thành phần đi kèm để đưa React lên trang web, không phải một framework bổ sung.

| Hạng mục | Công nghệ / cơ chế | Cách sử dụng |
| --- | --- | --- |
| Giao diện | React + React DOM | Functional components cho login, chat, lịch sử và ticket |
| Ngôn ngữ | JavaScript thuần | Logic giao diện, validation, mock adapter; dùng file `.js` |
| Thành phần trang | HTML thông qua React elements | Ưu tiên form, button, input, textarea, select và dialog tiêu chuẩn |
| Styling | CSS thuần + CSS custom properties | Tokens mục 3.2, responsive bằng media queries; không dùng thư viện CSS |
| State cục bộ | `useState`, `useRef` | Form, composer, menu, drawer và vị trí cuộn |
| State chia sẻ | `useReducer` + Context | Phiên demo, hội thoại và ticket; tách provider theo tính năng |
| Side effects | `useEffect` | Đồng bộ lưu trữ, theo dõi điều hướng, cleanup tác vụ đang chạy |
| Điều hướng | History API + `popstate` | Tự xây lớp điều hướng nhỏ cho các đường dẫn mục 4; hỗ trợ Back/Forward |
| Form / validation | Controlled inputs + JavaScript + HTML validation | Kiểm tra trường bắt buộc, email và độ dài; lỗi sát trường |
| Lưu trữ demo | localStorage + JSON | Schema version, kiểm tra dữ liệu khi đọc, xử lý lỗi và reset |
| Dữ liệu mẫu | JavaScript objects / JSON + mock adapters | Mô phỏng đăng nhập, câu trả lời, nguồn và ticket |
| Streaming mô phỏng | Timer / async generator + AbortController | Phát từng phần, dừng, cleanup và kiểm tra conversation ID |
| Hiển thị câu trả lời | React elements từ dữ liệu có cấu trúc | Paragraph, list, table và code block; không cài Markdown renderer |
| Icon | SVG tự tạo trong React | Icon đơn giản, có accessible name; không cài bộ icon |
| Ngày / ID | `Intl.DateTimeFormat`, `crypto.randomUUID()` | Ngày tiếng Việt và ID demo |
| Kiểm thử logic | JavaScript assertions trong trang kiểm thử nội bộ | Kiểm tra validation, nhóm ngày và dữ liệu lưu; không cài test framework |
| Kiểm thử giao diện | Trình duyệt và DevTools | Kiểm tra thủ công toàn luồng, responsive, focus và console |

**Cách chạy phù hợp với ràng buộc chỉ React:**

- Kế hoạch triển khai dùng JavaScript ES modules và `React.createElement` để không cần trình biên dịch JSX hoặc bundler bổ sung.
- React và React DOM phải được lấy từ cùng phiên bản tương thích, cố định phiên bản khi triển khai. Cách phân phối module được xác minh ở bước khởi tạo; không dùng URL `latest`.
- Phục vụ các file tĩnh qua HTTP bằng môi trường chạy sẵn có; đó là công cụ phục vụ file, không phải phần back-end của sản phẩm. Không mở trực tiếp bằng `file://`.
- Nếu sau này muốn dùng JSX hoặc công cụ build, phải cập nhật phạm vi công nghệ trước; hiện tại không đưa các công cụ đó vào stack.
- Với đường dẫn dạng `/chat/:id`, môi trường phục vụ cần fallback về `index.html`. Lớp điều hướng xử lý route không tồn tại, mở trực tiếp URL và Back/Forward.
- Không dùng thư viện router, store, form, validation, UI, Markdown, animation hoặc kiểm thử bổ sung.
- Context/provider là nguồn dữ liệu chung duy nhất; localStorage chỉ lưu bản sao để phục hồi, không là store phản ứng riêng.
- Không dùng `dangerouslySetInnerHTML` để render nội dung chat. Mock response lưu các khối có cấu trúc và render qua React elements.
- Công thức toán ở P1 dùng văn bản/ký hiệu hoặc MathML sau kiểm tra trình duyệt; chưa bổ sung thư viện render toán.
- Accessibility của dialog/drawer/menu cần tự kiểm tra: focus ban đầu, Tab, Escape, trả focus và accessible labels.

### 6.4. Tác động tới kế hoạch triển khai

- Bảng màu, màn hình và luồng sản phẩm giữ nguyên.
- Nội dung chat MVP hiển thị từ dữ liệu có cấu trúc, thay cho hỗ trợ Markdown tổng quát.
- Bổ sung việc tự xây điều hướng, validation và hành vi component vào giai đoạn nền giao diện.
- Ước lượng tổng thể tăng lên khoảng **18–25 ngày làm việc**, do cần tự triển khai và kiểm tra những phần trước đây giao cho thư viện.
- Kiểm thử UI theo checklist thủ công; kiểm thử logic bằng JavaScript thuần, không có test runner/E2E framework trong stack.
## 7. Component cần xây dựng

| Nhóm | Component |
| --- | --- |
| Layout | AppShell, Sidebar, MobileNavigation, PageHeader |
| Auth | LoginForm, PasswordField, DemoNotice |
| Chat | ChatEmptyState, PromptCard, MessageList, MessageItem, ChatComposer, MessageActions |
| Nguồn | CitationChip, SourceCard, SourcePanel |
| History | HistoryGroup, ConversationRow, HistorySearch, RenameDialog, DeleteDialog |
| Ticket | TicketForm, TicketList, TicketCard, StatusBadge, TicketDetail, TicketTimeline |
| Chung | Button, Input, Textarea, Select, Dialog, Drawer, Toast, Skeleton, EmptyState, ErrorState |

Mỗi component tương tác cần có trạng thái default, hover, focus, disabled và loading khi thích hợp.

## 8. Responsive và accessibility

- Mobile dưới khoảng 768 px: drawer sidebar, ticket dạng card, panel nguồn dạng sheet; tinh chỉnh breakpoint theo nội dung thực tế.
- Tablet: sidebar thu gọn hoặc drawer; bảo đảm vùng chat còn đủ chiều rộng.
- Desktop: sidebar cố định, hội thoại ở giữa, nguồn mở trong panel khi có đủ không gian.
- Kiểm tra ở 360, 390, 768, 1280 và 1440 px; bảng/code có vùng cuộn ngang riêng.
- Composer không bị bàn phím ảo che; kiểm tra đơn vị chiều cao viewport động.
- Mục tiêu accessibility: WCAG 2.2 AA; kiểm tra tương phản, label, focus, thứ tự tab, Escape đóng dialog và trả focus đúng chỗ.
- Nút chỉ có icon phải có accessible name; trạng thái ticket không chỉ phân biệt bằng màu.
- Đích chạm nên khoảng 44 px cho nút chính trên mobile.
- Thông báo phản hồi chat qua live region có tiết chế, tránh đọc từng ký tự streaming.
- Tôn trọng reduced motion; không dùng animation liên tục gây mất tập trung.

## 9. Dữ liệu mẫu và kịch bản demo

Chuẩn bị trước khi nối UI:

- Một tài khoản demo, không cần thông tin đăng nhập thật.
- Khoảng 8 hội thoại thuộc các nhóm thời gian và có tiêu đề dài/ngắn khác nhau.
- Câu trả lời mẫu: giải thích ngắn, câu trả lời dài, danh sách bước, bảng, code, câu có nguồn, câu thiếu nguồn.
- Khoảng 6 ticket phủ các trạng thái, gồm ticket liên kết hội thoại và ticket độc lập.
- Tên tài liệu và quy định học tập mẫu được đánh dấu rõ ràng.
- Kịch bản lỗi: đăng nhập thất bại, phản hồi gián đoạn, dừng giữa chừng, gửi ticket lỗi, ID không tồn tại, dữ liệu lưu bị lỗi.
- Kịch bản biên: nội dung tiếng Việt có dấu, tiêu đề rất dài, nhiều dòng, link dài, lịch sử rỗng.

Có chế độ chọn kịch bản trong môi trường phát triển; không đặt điều khiển kỹ thuật vào luồng sử dụng chính.

## 10. Lộ trình triển khai

Ước lượng cho một lập trình viên front-end làm toàn thời gian: khoảng **18–25 ngày làm việc**, chưa gồm thời gian chờ phản hồi thiết kế. Đây là dự kiến, cần điều chỉnh theo năng lực và mức độ hoàn thiện mong muốn.

| Giai đoạn | Dự kiến | Công việc | Điều kiện hoàn thành |
| --- | --- | --- | --- |
| 1. Chốt UX | 2–3 ngày | User flow, wireframe 4 nhóm màn hình, tokens, desktop/mobile | Mọi luồng chính và lỗi đều có cách xử lý |
| 2. Nền giao diện | 4–5 ngày | Khởi tạo React SPA, điều hướng History API, shell, component cơ bản, fixture | Điều hướng và bố cục responsive hoạt động |
| 3. Login demo | 1–2 ngày | Form, validation, session, guard, logout | Login/logout và mở route trực tiếp đúng |
| 4. Chat + nguồn | 4–5 ngày | Composer, messages, stream mock, dừng/thử lại, citation | Chat có đủ trạng thái và không trộn hội thoại |
| 5. Lịch sử | 2 ngày | Tìm kiếm, nhóm ngày, đổi tên, xóa, persistence | Mở lại dữ liệu sau reload và thao tác đúng |
| 6. Ticket | 2–3 ngày | Form, list, detail, liên kết từ chat, lỗi submit | Tạo và xem ticket demo từ đầu đến cuối |
| 7. Hoàn thiện | 3–5 ngày | Mobile, accessibility, kiểm thử, sửa lỗi, hướng dẫn demo | Đạt checklist nghiệm thu |

Thứ tự phụ thuộc: tokens/fixture → shell/login → chat → lịch sử và ticket → kiểm thử toàn luồng. Có thể thiết kế form ticket trong lúc hoàn thiện đặc tả chat, nhưng không mở rộng sang back-end.

## 11. Backlog ưu tiên

### P0 — bắt buộc trước demo

- [ ] Tokens và app shell responsive.
- [ ] Login demo, validation, route guard, logout.
- [ ] Chat mới, gửi câu hỏi, trả lời giả lập, dừng và thử lại.
- [ ] Hiển thị và mở đúng nguồn tham khảo mẫu.
- [ ] Lịch sử: mở, tìm kiếm tiêu đề, đổi tên, xóa.
- [ ] Lưu và phục hồi dữ liệu demo sau reload.
- [ ] Tạo ticket từ menu hoặc từ câu trả lời.
- [ ] Danh sách/chi tiết ticket và các trạng thái mẫu.
- [ ] Trạng thái rỗng, loading, lỗi và ID không tồn tại.
- [ ] Kiểm thử mobile và bàn phím.

### P1 — sau khi P0 ổn định

- [ ] Render công thức toán nếu bài tập mục tiêu yêu cầu.
- [ ] Phản hồi hữu ích/chưa hữu ích và sao chép câu trả lời.
- [ ] Tinh chỉnh typography và micro-interactions.
- [ ] Ghim/lưu trữ hội thoại nếu cần cho demo mở rộng.

### P2 — phiên bản tiếp theo

- [ ] Dark mode và chuyển ngôn ngữ.
- [ ] Đính kèm tài liệu với tiến trình và trạng thái lỗi mô phỏng.
- [ ] Xuất hội thoại và trao đổi bổ sung trong ticket.
- [ ] Giao diện SSO sau khi xác nhận yêu cầu IU.

## 12. Kiểm thử và nghiệm thu

### 12.1. Kiểm thử cần thực hiện

- Kiểm thử logic bằng JavaScript assertions: validation form, nhóm ngày lịch sử, persistence và xử lý dữ liệu hỏng.
- Kiểm thử component thủ công: composer, dialog xóa, form ticket, citation mapping.
- Kiểm thử tích hợp trong trình duyệt: mock adapter với loading/error/hủy; đổi hội thoại khi đang nhận phản hồi.
- Kiểm thử toàn luồng thủ công: login demo → chat → nguồn → reload → mở lịch sử → tạo ticket → xem chi tiết → logout; thêm Back/Forward và mở URL trực tiếp.
- Kiểm tra thủ công: mobile keyboard, nội dung dài, zoom 200%, keyboard navigation và một lượt screen reader.

### 12.2. Checklist nghiệm thu MVP

- [ ] Người dùng xác định được chat mới, lịch sử và ticket ngay từ app shell.
- [ ] Không có nút chính không hoạt động hoặc liên kết nguồn giả.
- [ ] Mọi form báo lỗi sát trường và giữ dữ liệu khi thao tác thất bại.
- [ ] Dừng trả lời và chuyển chat không gây cập nhật nhầm dữ liệu.
- [ ] Citation dẫn tới đúng đoạn trích tương ứng.
- [ ] Xóa chat đang mở điều hướng đúng; ticket giữ trích đoạn sau khi chat bị xóa.
- [ ] Reload giữ lịch sử/ticket demo và phiên theo quy ước đã chọn.
- [ ] Không có cuộn ngang toàn trang trên mobile; ô nhập vẫn dùng được khi mở bàn phím.
- [ ] Truy cập mọi thao tác chính bằng bàn phím, focus luôn nhìn thấy.
- [ ] Hiển thị rõ giới hạn của bản demo và trạng thái nguồn mẫu.
- [ ] Ứng dụng chạy từ file tĩnh qua HTTP; kiểm tra cấu trúc dữ liệu hợp lệ và không có lỗi console trong luồng chính.

## 13. Rủi ro và cách kiểm soát

| Rủi ro | Cách xử lý trong front-end |
| --- | --- |
| Phong cách Studocu làm giao diện chat quá nhiều chi tiết | Dùng pastel ở login/empty state, giữ hội thoại tối giản |
| Người dùng tưởng câu trả lời mẫu là dữ liệu IU thật | Gắn nhãn demo và nguồn mẫu tại vị trí liên quan |
| Câu trả lời dài làm trải nghiệm mobile kém | Giới hạn chiều rộng đọc, cuộn riêng bảng/code, composer responsive |
| Dữ liệu localStorage lỗi hoặc đầy | Kiểm tra schema, xử lý lỗi lưu, cho reset dữ liệu demo |
| Chuyển chat khi stream chưa kết thúc | Gắn tác vụ với conversation ID, hủy khi cần, kiểm tra trước cập nhật |
| Phạm vi tăng sang upload, SSO, dashboard quản trị | Giữ P0 làm điều kiện demo, đưa tính năng thêm vào backlog |
| Adapter thật sau này có khác biệt | Tách model UI và adapter, ghi rõ giả định để điều chỉnh khi tích hợp |

## 14. Deliverables front-end

1. Wireframe desktop/mobile cho login, chat/lịch sử, ticket list/form/detail.
2. Bộ tokens và component UI có trạng thái rõ ràng.
3. SPA chạy được với mock adapter và dữ liệu demo.
4. Các kịch bản kiểm thử và checklist nghiệm thu.
5. Hướng dẫn chạy, reset dữ liệu demo và ghi chú các interface cần nối sau này.

**Bước triển khai đầu tiên:** vẽ wireframe login và app shell chat, chốt tokens, rồi xây một luồng dọc nhỏ gồm đăng nhập demo → gửi một câu hỏi → xem một nguồn. Sau khi luồng này ổn định, mở rộng lịch sử và ticket.

