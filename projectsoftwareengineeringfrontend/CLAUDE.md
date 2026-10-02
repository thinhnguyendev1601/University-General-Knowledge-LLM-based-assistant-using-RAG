# CLAUDE.md — Website Trợ lý Hỏi đáp cho Đại học (Frontend)

Tài liệu này là nguồn chuẩn cho mọi thay đổi trong dự án. Đọc trước khi viết code.

## 1. Mô tả dự án

Website của trường đại học, thiết kế theo kiểu ChatGPT: người dùng đặt câu hỏi, hệ thống trả lời dựa trên **kho dữ liệu sẵn có** (FAQ, lịch học, quy chế, học bổng, thủ tục...). Giao diện tối giản, sạch, chuyên nghiệp.

**Luật bắt buộc — CHỈ React, không dùng gì khác:** Toàn bộ website **chỉ được xây dựng bằng React**. Mọi UI, logic phía client, và cấu trúc component đều phải là React component. Tuyệt đối không dùng framework thay thế (Vue, Angular, Svelte, Solid, Preact, Next.js...), không dùng thư viện UI/JS khác để dựng giao diện, và không viết UI thuần HTML/CSS/JS nằm ngoài React (kể cả khi chỉ là một đoạn nhỏ). Mọi tương tác, state, routing, và render đều đi qua React.

**Phạm vi: CHỈ FRONTEND.** Không viết backend, không viết database, không deploy. Mọi dữ liệu đến từ API — khi API chưa sẵn có thì dùng mock service giả lập đúng hợp đồng dữ liệu.

**Luật bắt buộc — tính năng phụ thuộc backend:** Khi lập kế hoạch hoặc triển khai tính năng ở mục 5, nếu một tính năng **cần backend thật mới chạy được** (đăng nhập xác thực, quên mật khẩu, refresh token, trả lời từ kho dữ liệu, streaming, đồng bộ hội thoại, quản trị dữ liệu admin...) thì: **không làm tính năng đó, bỏ qua**, và ghi tên tính năng, lý do, nguồn API cần có vào file `BACKEND_BLOCKED_FEATURES.md` ở thư mục gốc. Chỉ làm phần UI/UX còn lại, dùng mock tại `src/mocks/` để test, và tuyệt đối không giả lập hay hardcode logic nghiệp vụ phía server trong frontend.

## 2. Công nghệ

| Hạng mục | Lựa chọn |
|---|---|
| Framework | React 18 + TypeScript (bắt buộc, không dùng JS thuần) |
| Build | Vite |
| Routing | React Router v6 |
| State server | TanStack Query (React Query) |
| State client | Zustand (chỉ cho UI state: mở/đóng chat, theme) |
| Styling | CSS Modules + CSS variables (KHÔNG dùng Tailwind, không dùng UI library nặng) |
| Form | React Hook Form + Zod |
| Lint | ESLint + Prettier |
| Test | Vitest + React Testing Library |

Lý do: tối thiểu phụ thuộc, dễ bàn giao cho team khác, dễ mở rộng sau này.

## 3. Cấu trúc thư mục

```
src/
├── app/            # Khởi tạo app, providers, router
├── pages/          # Một folder cho mỗi route (chỉ ghép layout, không chứa logic)
├── features/       # Nghiệp vụ chia theo domain
│   ├── auth/
│   ├── chat/
│   └── home/
├── components/     # Component dùng chung, không thuộc domain nào
│   └── ui/         # Button, Input, Modal, Spinner...
├── hooks/          # Custom hook dùng chung
├── services/       # Hàm gọi API. Chỉ có network, không có business logic
├── types/          # TypeScript types & interfaces
├── mocks/          # Dữ liệu giả lập cho dev
├── styles/         # globals.css, variables
├── utils/          # Hàm thuần, không phụ thuộc React
└── assets/
```

**Quy tắc vàng:** component trong `features/X/` không được import trực tiếp từ `features/Y/`. Chúng đi qua `components/ui` hoặc `hooks`.

## 4. Quy ước code

- **Typing:** không dùng `any`. Dùng `unknown` rồi narrow. Mọi API response có type tương ứng trong `types/`.
- **Naming:** file component dạng `PascalCase.tsx` (`ChatWidget.tsx`), file khác dạng `camelCase.ts` (`formatDate.ts`).
- **Component:** function component + hook. Class component chỉ khi thật sự cần lifecycle phức tạp.
- **Props:** luôn định nghĩa `interface XxxProps` cạnh component, không inline type.
- **Một component một file.** File dài quá ~150 dòng → tách.
- **Comment:** viết *tại sao*, không viết *cái gì*. Comment tiếng Việt được chấp nhận.
- **Import:** dùng `@/` alias (đã cấu hình sẵn trong `vite.config.ts` và `tsconfig.json`).
- **Không** dùng `any`, không dùng biến 1 chữ trừ `i` trong `map`, không commit file `.env`.

## 5. Tính năng bắt buộc

### 5.1 Trang Login (`/login`)
- Đăng nhập bằng email + mật khẩu.
- **2 role: `admin` và `user`.** Role nằm trong response login, lưu vào auth store.
- Validate bằng Zod, hiển thị lỗi ngay dưới field.
- Nút tắt/đổi mật khẩu (quên mật khẩu) — giao diện có, chưa cần API thật.
- Báo lỗi sai thông tin: hiển thị alert/message rõ ràng, không console.log.

### 5.2 Phân quyền
- Route bảo vệ: `<RequireAuth>` và `<RequireRole role="admin">` (component trong `features/auth`).
- Không ẩn/hiện UI là biện pháp bảo mật — frontend chỉ là lớp UX, backend mới là nơi thực thi.
- Admin thấy thêm menu **Quản lý dữ liệu** (đang để placeholder, chưa cần build đầy đủ).

### 5.3 Trang chủ (`/`)
- Landing page tối giản: tên trường, slogan ngắn, và nút mở khung chat.
- **Nút bấm → mở khung chat nhỏ (widget) dạng panel trượt vào**, không phải trang riêng. Widget nằm cố định góc phải dưới màn hình.
- Widget có: header (tên trợ lý, nút đóng), danh sách tin nhắn, ô nhập, nút gửi.
- Widget có thể thu gọn lại thành nút tròn nhỏ.

### 5.4 Khung chat — hành vi giống ChatGPT
- Gửi tin bằng Enter, xuống dòng bằng `Shift+Enter`.
- **Streaming / typing indicator:** hiển thị "đang trả lời..." với hiệu ứng gõ khi chờ server.
- **Auto-scroll** xuống cuối danh sách tin mỗi khi có tin mới.
- **Lưu lịch sử chat:** mỗi cuộc hội thoại có `conversationId`, danh sách hội thoại lưu `localStorage`.
  - Tạo hội thoại mới, đổi tên tự động từ câu hỏi đầu tiên.
  - Xoá một hội thoại.
  - Xoá tất cả.
  - Khi reload trang, hội thoại và tin nhắn được khôi phục nguyên vẹn.
- **Xử lý lỗi:** lỗi mạng / server → hiện thông báo trong khung chat kèm nút **Thử lại**, không mất nội dung đã gõ.
- **Paste nhiều dòng / text dài:** hiển thị đúng, không phá layout.
- **Responsive:** trên mobile widget chiếm toàn màn hình.

## 6. Hợp đồng API (chốt trước, backend làm theo)

Tất cả request đi qua `services/`, dùng chung một `httpClient` duy nhất (timeout, header `Authorization: Bearer <token>`, parse lỗi thống nhất, refresh token).

```
POST /api/auth/login        { email, password } → { token, refreshToken, user: { id, name, email, role: 'admin'|'user' } }
GET  /api/chat/conversations                  → ChatConversation[]
GET  /api/chat/conversations/:id/messages      → ChatMessage[]
POST /api/chat/messages  { conversationId, content } → ChatMessage   (stream hoặc polling, tuỳ backend)
DELETE /api/chat/conversations/:id
```

```ts
type Role = 'admin' | 'user'

interface User {
  id: string
  name: string
  email: string
  role: Role
}

interface ChatMessage {
  id: string
  conversationId: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string // ISO 8601
}

interface ChatConversation {
  id: string
  title: string
  updatedAt: string
}
```

Khi backend chưa có, `mocks/` cung cấp dữ liệu giả với cùng kiểu dữ liệu và cùng độ trễ (delay) để UI test được. **Không được rải `if (mock)` rong lung tung trong component** — chỉ đổi implementation trong `services/`.

## 7. Bảng thiết kế màu (Design tokens)

Hai theme: **light** (mặc định) và **dark**, đổi qua `data-theme` trên `<html>`.

**Nguyên tắc:** xanh dương thương hiệu = màu nhấn; phần còn lại là trung tính lạnh (xám hơi xanh) để giữ cảm giác học thuật, sạch, chuyên nghiệp. Tỷ lệ color usage: ~60% nền trung tính, ~30% bề mặt, ~10% màu nhấn.

### 7.1 Light mode

| Token | Hex | Dùng cho |
|---|---|---|
| `--color-primary` | `#1D4ED8` (blue-700) | nút chính, link, focus, avatar user |
| `--color-primary-hover` | `#1E40AF` (blue-800) | hover nút chính |
| `--color-primary-soft` | `#EFF6FF` (blue-50) | nền badge/tooltip nhẹ, bubble chat admin tint |
| `--color-bg` | `#F8FAFC` (slate-50) | nền trang |
| `--color-surface` | `#FFFFFF` | card, panel chat, ô input |
| `--color-surface-muted` | `#F1F5F9` (slate-100) | nền sidebar lịch sử chat, skeleton |
| `--color-border` | `#E2E8F0` (slate-200) | đường kẻ, viền input |
| `--color-border-strong` | `#CBD5E1` (slate-300) | viền khi hover/focus input |
| `--color-text` | `#0F172A` (slate-900) | tiêu đề, nội dung chính |
| `--color-text-body` | `#334155` (slate-700) | nội dung thân bài, câu trả lời chat |
| `--color-text-muted` | `#64748B` (slate-500) | meta (thời gian, mô tả phụ) |
| `--color-text-inverse` | `#FFFFFF` | chữ trên nền primary |
| `--color-success` | `#16A34A` | trạng thái thành công |
| `--color-warning` | `#D97706` | cảnh báo |
| `--color-danger` | `#DC2626` | lỗi, nút xoá, destructive |
| `--color-success-bg` | `#F0FDF4` | nền badge success |
| `--color-warning-bg` | `#FFFBEB` | nền badge warning |
| `--color-danger-bg` | `#FEF2F2` | nền badge lỗi |

### 7.2 Dark mode

| Token | Hex | Ghi chú |
|---|---|---|
| `--color-primary` | `#3B82F6` (blue-500) | sáng hơn để đọc trên nền tối |
| `--color-primary-hover` | `#60A5FA` (blue-400) | |
| `--color-primary-soft` | `#1E3A8A` (blue-900/40%) | nền tint admin bubble |
| `--color-bg` | `#0F172A` (slate-900) | nền trang |
| `--color-surface` | `#1E293B` (slate-800) | card, panel chat |
| `--color-surface-muted` | `#334155` (slate-700) | sidebar lịch sử, input phụ |
| `--color-border` | `#334155` (slate-700) | viền |
| `--color-border-strong` | `#475569` (slate-600) | viền focus |
| `--color-text` | `#F8FAFC` (slate-50) | |
| `--color-text-body` | `#E2E8F0` (slate-200) | |
| `--color-text-muted` | `#94A3B8` (slate-400) | |
| `--color-success` | `#22C55E` | |
| `--color-warning` | `#F59E0B` | |
| `--color-danger` | `#EF4444` | |

### 7.3 Quy tắc dùng màu trong UI

- **Bubble chat người dùng:** nền `--color-primary`, chữ `--color-text-inverse`, bo góc `16px 16px 4px 16px`.
- **Bubble chat assistant (AI):** nền `--color-surface-muted` (light) / `--color-surface` (dark), chữ `--color-text-body`, bo góc `16px 16px 16px 4px`. Không dùng màu sáng chói — giữ cảm giác bot trung lập.
- **Nút chính (`primary`):** nền `--color-primary`, hover `--color-primary-hover`, active scale `0.98`, transition `150ms`.
- **Nút phụ:** nền trong suốt, viền `--color-border`, hover nền `--color-surface-muted`.
- **Focus ring:** `box-shadow: 0 0 0 3px var(--color-primary-soft)` — luôn hiện khi keyboard focus.
- **Không** dùng `--color-primary` làm màu nền của trang hay khối lớn >30% viewport.

### 7.4 Chữ (Typography)

- Font family: `"Inter", -apple-system, "Segoe UI", Roboto, sans-serif`.
- `--font-size-xs`: 12px (meta, badge) · `--font-size-sm`: 14px · `--font-size-base`: 16px (nội dung chat) · `--font-size-lg`: 18px · `--font-size-xl`: 24px (heading trang) · `--font-size-2xl`: 32px (hero).
- Line-height thân bài: 1.5; heading: 1.2.
- Nội dung chat dùng `--font-size-base` để dễ đọc; meta thời gian dùng `--font-size-xs` + `--color-text-muted`.

### 7.5 Khoảng cách, bo góc, bóng (Spacing / Radius / Shadow)

- `--space-1` 4px · `--space-2` 8px · `--space-3` 12px · `--space-4` 16px · `--space-6` 24px · `--space-8` 32px · `--space-12` 48px.
- `--radius-sm` 6px (badge, chip) · `--radius-md` 10px (input, card) · `--radius-lg` 16px (panel chat, bubble lớn) · `--radius-full` 9999px (avatar, nút tròn).
- `--shadow-sm`: `0 1px 2px rgba(15,23,42,0.06)` — card nhẹ.
- `--shadow-md`: `0 4px 16px rgba(15,23,42,0.08)` — panel chat.
- `--shadow-lg`: `0 12px 32px rgba(15,23,42,0.12)` — modal.

Đặt toàn bộ token ở `src/styles/variables.css`, ánh xạ biến theo `:root` và `[data-theme="dark"]`. Không hardcode hex rải rác trong component — mọi màu đều đi qua token.

## 7b. Bảng các branch (Git)

Tách branch theo **tính năng (feature-branch workflow)**, làm trên nhánh `develop`, gộp về `main` chỉ khi release. Fasta-forward merge khi có thể, dùng merge commit rõ ràng khi cần review.

### 7b.1 Chuỗi branch chính

```
main
 └─ develop
     ├─ feature/login-page
     ├─ feature/auth-guard
     ├─ feature/chat-widget
     ├─ feature/chat-history
     ├─ feature/chat-styling
     ├─ feature/home-landing
     ├─ feature/theme-darkmode
     ├─ chore/project-setup
     └─ fix/… (bất cứ khi nào sửa bug)
```

### 7b.2 Chi tiết từng branch

| Tên branch | Nội dung | Phụ thuộc | Definition of Done |
|---|---|---|---|
| `chore/project-setup` | Scaffold Vite + React + TS, ESLint/Prettier, cấu trúc thư mục, import alias `@/`, Vitest. Tạo luôn `CLAUDE.md` + token CSS nền (light/dark rỗng). | – | `npm run lint`, `typecheck`, `test`, `build` đều pass. Merge vào `develop` trước tiên. |
| `feature/login-page` | Trang `/login`, form email+mật khẩu, validate Zod, gọi `POST /api/auth/login` (có mock), lưu token + user vào auth store (Zustand + localStorage). | `chore/project-setup` | Validate hiển thị lỗi đúng dưới field; login sai hiện message rõ ràng; state giữ nguyên khi lỗi. |
| `feature/auth-guard` | `RequireAuth` + `RequireRole` wrapper, route protection cho `/` và `/admin`. Điều hướng sau login theo role. | `feature/login-page` | Chưa login → redirect `/login`; `user` vào `/admin` → redirect về `/`; refresh trang vẫn giữ session. |
| `feature/chat-widget` | Widget góc phải dưới: mở/đơn, nút tròn thu gọn, panel trượt có header/input/list. Gửi tin Enter (Shift+Enter xuống dòng), typing indicator "đang trả lời...", auto-scroll. Gọi API qua `services/chat` với mock. | `feature/auth-guard` | Gửi + nhận tin hiển thị đúng, indicator hiện khi chờ, auto-scroll hoạt động, responsive mobile (widget chiếm full màn hình). |
| `feature/chat-history` | Lưu lịch sử vào `localStorage`: tạo hội thoại mới, đổi tên từ câu hỏi đầu tiên, xoá 1/tất cả, khôi phục sau reload. Gắn với `conversationId`. | `feature/chat-widget` | Reload trang chat vẫn nguyên; đổi tên + xoá hoạt động; danh sách hội thoại hiển thị đúng thứ tự mới nhất. |
| `feature/chat-styling` | Bong bóng chat theo bảng màu mục 7.3, sidebar lịch sử, trạng thái rỗng (empty state), nút "Thử lại" khi lỗi, dark mode cho toàn bộ chat. | `feature/chat-history` | Đúng token màu ở mục 7; bubble user/assistant phân biệt rõ; lỗi mạng hiện nút Thử lại; không hardcode hex. |
| `feature/home-landing` | Trang `/` tối giản: tên trường, slogan, CTA mở chat widget, thanh nav có link login/avatar role. | `feature/chat-widget` | Giao diện tối giản đúng hướng thiết kế; CTA mở chat hoạt động; responsive. |
| `feature/theme-darkmode` | Chuyển theme light/dark, persist lựa chọn, toggle ở header + ưu tiên `prefers-color-scheme`. | `feature/chat-styling`, `feature/home-landing` | Toggle hoạt động không nháy (FOUC) sau reload; toàn bộ trang đọc được ở cả 2 theme. |
| `fix/*` | Sửa bug — đặt tên `fix/<mô tả ngắn>`, kéo từ nhánh đang ảnh hưởng. | – | Có mô tả rõ bug + cách sửa trong commit/PR. |
| `release/v1.0` | Gộp feature đã duyệt, chạy test + build cuối, chuẩn bị lên `main`. | mọi feature | Lint/typecheck/test/build pass; checklist ở mục 8 hoàn tất. |

### 7b.3 Quy tắc đặt tên & hợp nhất

- **Định dạng:** `<loại>/<mô-tả-kebab-case>` — `feature/chat-history`, `fix/auto-scroll-bug`, `chore/update-deps`.
- **Loại:** `feature`, `fix`, `chore`, `refactor`, `docs`, `release`.
- **Nguyên tắc:** mỗi PR = 1 branch = 1 tính năng hoàn chỉnh; không trộn tính năng và fix trong cùng 1 branch.
- **Review:** PR tự review + 1 người duyệt trước khi merge vào `develop`.
- **Cấm:** force-push lên `main`/`develop`; commit trực tiếp vào `main` (chỉ `release/*` được merge vào `main`).
- **Khi backend chưa có:** branch vẫn làm được vì mọi network đi qua `services/` — chỉ đổi implementation mock/thật trong `services/`, không sửa component.

## 9. Quy trình làm việc

1. Đọc mục liên quan trong file này trước khi code.
2. Kiểm tra code hiện có trước khi tạo thêm thứ mới — ưu tiên sửa/mở rộng hơn là tạo mới.
3. Component mới kiểu chức năng → đặt trong `features/` tương ứng, không nhét vào `pages/`.
4. Sau mỗi thay đổi: chạy `npm run lint`, `npm run typecheck`, `npm run build`. Không để lỗi TypeScript.
5. Component có logic hoặc UI đáng kể → viết test cùng file (`__tests__/`).
6. Commit message tiếng Anh, format Conventional Commits: `feat:`, `fix:`, `refactor:`, `style:`, `chore:`.

## 10. Lệnh dự án

```bash
npm run dev        # chạy dev server
npm run build      # build production
npm run preview    # xem bản build
npm run lint       # ESLint
npm run typecheck  # tsc --noEmit
npm run test       # Vitest
```

## 11. Việc KHÔNG làm trong dự án này

- ❌ Dùng bất kỳ framework UI nào khác ngoài React (Vue, Angular, Svelte, Solid, Preact, Next.js...) hoặc viết UI thuần HTML/CSS/JS không qua React.
- ❌ Viết backend, database, hay deploy.
- ❌ Làm tính năng nào ở mục 5 mà cần backend thật mới chạy được — bỏ qua tính năng đó và ghi vào `BACKEND_BLOCKED_FEATURES.md` thay vì cố gắng giả lập logic server trong frontend.
- ❌ Hardcode dữ liệu nghiệp vụ trong component (phải qua `services/` + `mocks/`).
- ❌ Bỏ qua TypeScript bằng `as any` hoặc `@ts-ignore`.
- ❌ Thêm thư viện mới mà không hỏi lại.
- ❌ Dùng emoji làm icon; dùng SVG inline hoặc icon library nhẹ.
- ❌ Commit secret, token, `.env`.
