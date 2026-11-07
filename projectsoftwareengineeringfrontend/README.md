# Trợ lý Hỏi đáp Đại học — Frontend

Website trợ lý hỏi đáp cho trường đại học, giao diện kiểu ChatGPT. Sinh viên đặt
câu hỏi về lịch học, học bổng, thủ tục, quy chế và nhận câu trả lời từ kho dữ
liệu của trường.

UI viết bằng React + TypeScript. Đăng ký, đăng nhập bằng cookie,
đăng xuất và đặt lại mật khẩu đã nối FastAPI/PostgreSQL thật. Chat nối API RAG;
lịch sử được lưu trên PostgreSQL và tải lại theo phiên đăng nhập. Xem [hướng dẫn chạy ở README gốc](../README.md)
để khởi động database và áp dụng migration trước khi mở giao diện. Đăng ký chỉ
kiểm tra tên miền `university.edu.vn`, không yêu cầu xác minh email.

---

## 1. Yêu cầu môi trường

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Node.js | >= 20.19 (khuyến nghị 22 LTS trở lên) | Vite 8 cần Node mới |
| npm | >= 10 | đi kèm Node |

Kiểm tra nhanh:

```bash
node -v
npm -v
```

Nếu Node cũ hơn 20.19, tải bản mới tại <https://nodejs.org> rồi mở lại terminal.

---

## 2. Cài đặt

Mở terminal tại thư mục gốc dự án (nơi có `package.json`):

```bash
npm install
```

Lệnh này tải toàn bộ thư viện vào `node_modules/`. Chạy một lần sau khi clone,
hoặc chạy lại khi `package.json` thay đổi.

> Nếu gặp lỗi mạng/registry, thử `npm install --no-audit --no-fund`.

---

## 3. Chạy ở chế độ phát triển

```bash
npm run dev
```

Terminal in ra địa chỉ local:

```
VITE v8.3.2  ready in 244 ms

➜  Local:   http://localhost:5173/
```

Mở <http://localhost:5173> trên trình duyệt. Server có **hot reload**: sửa file
trong `src/` rồi lưu, trình duyệt tự cập nhật, không cần tải lại trang.

Một số tuỳ chọn hay dùng:

```bash
npm run dev -- --port 3000   # đổi cổng nếu 5173 đang bị chiếm
npm run dev -- --host        # cho máy khác trong cùng mạng LAN truy cập
npm run dev -- --open        # tự mở trình duyệt
```

Dừng server: nhấn `Ctrl + C` trong terminal.

### 3.1 Đăng nhập thử

Trang `/` được bảo vệ nên vào lần đầu sẽ chuyển về `/login`. Mở `/register`,
đăng ký email có tên miền chính xác `university.edu.vn` và mật khẩu 15–128 ký tự.
Tài khoản được kích hoạt ngay, có thể đăng nhập mà không mở email. Các tài
khoản/mật khẩu demo cũ được hiển thị lại thành hai dòng tham khảo trên trang
đăng nhập; database hiện không tự tạo các tài khoản này.

Frontend phục hồi phiên bằng `/api/auth/me`; không lưu token đăng nhập vào
localStorage. Lịch sử lấy từ server; đăng xuất/đổi tài khoản xóa bản hiển thị
trong RAM, không xóa lịch sử PostgreSQL. Khi phát
triển, Mailpit nhận email đặt lại mật khẩu trong máy; gửi ra hộp thư thật cần
cấu hình SMTP. SMTP không cần cho đăng ký hoặc đăng nhập.

### 3.2 Thử khung chat

1. Ở trang chủ, bấm **Hỏi ngay** (hoặc nút tròn góc phải dưới) để mở widget.
2. Gõ câu hỏi, nhấn `Enter` để gửi; `Shift + Enter` để xuống dòng.
3. Trong lúc chờ, widget hiện "Đang trả lời..." với hiệu ứng gõ.
4. Bấm icon ba gạch trên header widget để xem **lịch sử hội thoại**: tạo mới,
   đổi tên, xoá một, xoá tất cả qua API server.
5. Tải lại trang (`F5`) hoặc đăng nhập lại — hội thoại/tin nhắn được đọc lại
   từ PostgreSQL theo tài khoản. Không tự nhập lịch sử local cũ.
6. Thu nhỏ cửa sổ dưới 480px để thấy widget chiếm toàn màn hình (chế độ mobile).

### 3.3 Thử luồng lỗi mạng và nút "Thử lại"

Chat gọi API thật; service không còn nhánh `VITE_USE_MOCK_CHAT`. Lỗi mạng/
model giữ câu hỏi và requestId để **Thử lại**, kể cả sau reload. Khi backend
bận hoặc timeout, UI dùng message/Retry-After và HTTP budget từ server.
Chạy `npm.cmd test` để kiểm tra lỗi bằng adapter được mock trong kiểm thử,
không cần tạo lỗi giả trong dữ liệu thật. Chi tiết:
[B4 và lịch sử server](../docs/08_project_changes_and_handover.md).

---

## 4. Các lệnh khác

| Lệnh | Việc nó làm |
|---|---|
| `npm run dev` | Chạy dev server kèm hot reload |
| `npm run build` | Build production vào `dist/` (có typecheck trước) |
| `npm run preview` | Chạy thử bản đã build, mặc định cổng 4173 |
| `npm run lint` | ESLint trên `src/` |
| `npm run format` | Prettier tự sửa định dạng trong `src/` |
| `npm run format:check` | Kiểm tra định dạng, không sửa |
| `npm run typecheck` | `tsc --noEmit`, bắt lỗi TypeScript |
| `npm run test` | Vitest chạy một lượt rồi thoát |
| `npm run test:watch` | Vitest ở chế độ theo dõi file |

Trước khi commit, nên chạy đủ bộ:

```bash
npm run lint && npm run typecheck && npm run test && npm run build
```

---

## 5. Xem bản build production

```bash
npm run build
npm run preview
```

`preview` phục vụ nội dung trong `dist/` tại <http://localhost:4173>. Đây là
bản tĩnh đã tối ưu, không có hot reload.

---

## 6. Cấu trúc thư mục

```
src/
├── app/            # (dành cho providers/router khi tách khỏi App.tsx)
├── pages/          # Một folder/file cho mỗi route, chỉ ghép layout
├── features/       # Nghiệp vụ theo domain
│   ├── auth/       # Login, auth store, RequireAuth, RequireRole
│   ├── chat/       # ChatWidget + các phần con, chat store, useChat
│   └── home/       # Landing page
├── components/     # Component dùng chung
│   └── ui/         # Button, Input, Spinner
├── hooks/          # useUIStore (theme, mở/đóng chat)
├── services/       # Gọi API — chỉ network, không business logic
├── types/          # TypeScript types theo hợp đồng API
├── mocks/          # Dữ liệu giả lập khi chưa có backend
├── styles/         # variables.css (design token), globals.css
├── test/           # Setup cho Vitest
└── utils/          # Hàm thuần
```

### Hợp đồng backend hiện tại

`src/services/chat.ts` gọi API tạo/đọc/đổi tên/xóa hội thoại và đọc tin nhắn.
Tạo hội thoại trước khi gửi; retry giữ nguyên requestId và institutionId.
Xem [tổng hợp thay đổi hội thoại](../docs/08_project_changes_and_handover.md). State ở RAM
chỉ phục vụ hiển thị, không thay thế dữ liệu server.

---

## 7. Xử lý sự cố thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `Port 5173 is in use` | `npm run dev -- --port 3000` |
| Lỗi `Cannot find module '@/...'` | Chạy lại `npm install`; alias `@/` khai báo ở `vite.config.ts` và `tsconfig.app.json` |
| Trang trắng sau khi sửa code | Mở DevTools → Console xem lỗi; chạy `npm run typecheck` |
| Vào `/` lại bị đẩy về `/login` | Chưa đăng nhập hoặc phiên hết hạn — đăng ký/đăng nhập theo mục 3.1 |
| `user` vào `/admin` bị đẩy về `/` | Đúng thiết kế, `/admin` chỉ dành cho role `admin` |
| Xóa lịch sử báo lỗi hoặc xuất hiện lại | Kiểm tra kết quả API DELETE, phiên đăng nhập và dùng Tải lại lịch sử; không sửa localStorage để thay dữ liệu server |
| Giao diện sai màu / mất theme | Kiểm tra `data-theme` trên thẻ `<html>`; đổi theme bằng nút trên header |
| `npm install` lỗi phiên bản | Kiểm tra `node -v` >= 20.19 |

---

## 8. Công nghệ

React 18+ / TypeScript · Vite · React Router v6 · TanStack Query · Zustand ·
CSS Modules + CSS variables · React Hook Form + Zod · ESLint + Prettier ·
Vitest + React Testing Library.

Chi tiết quy ước code, design token và quy trình branch: xem `CLAUDE.md`.
