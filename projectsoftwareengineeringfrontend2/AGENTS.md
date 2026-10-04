# Hướng dẫn Codex — IU Study Assistant

## Phạm vi và công nghệ

- Đọc phần liên quan trong `ke-hoach-front-end-iu-rag.md` trước khi triển khai. Đây là nguồn yêu cầu của dự án.
- MVP chỉ gồm front-end với dữ liệu giả: đăng nhập demo, chat, lịch sử và ticket. Không triển khai backend, RAG hoặc xác thực thật ngoài yêu cầu mới của người dùng.
- Stack đã chốt: React + React DOM, JavaScript ES modules, HTML và CSS thuần. Dùng `React.createElement`, History API và API trình duyệt theo kế hoạch.
- Không tự thêm TypeScript, JSX/bundler, Next.js, Tailwind, router, state library, bộ icon hoặc test framework. Chỉ thay đổi stack khi người dùng yêu cầu.
- UI mặc định tiếng Việt; tuân thủ semantic tokens, responsive và keyboard navigation trong kế hoạch.

## Skill của dự án

Skill được lưu trong `.agents/skills/`. Chỉ đọc skill phù hợp với công việc hiện tại:

| Skill | Khi áp dụng |
| --- | --- |
| `coding-standards` | Viết/sửa JavaScript, đặt tên, tổ chức module và refactor |
| `frontend-patterns` | Component React, hooks, state, form, responsive và accessibility |
| `documentation-lookup` | Tra cứu API và hành vi thư viện qua Context7 nếu có kết nối |
| `requesting-code-review` | Review tính năng lớn hoặc trước khi merge, theo workflow và template của skill |

Các ví dụ TypeScript, JSX, Next.js hoặc thư viện bổ sung trong skill chỉ là tham khảo về nguyên tắc; áp dụng bằng stack đã chốt của dự án. Không coi ví dụ là yêu cầu cài dependency.

Nếu Context7 không khả dụng, thông báo ngắn gọn và dùng tài liệu chính thức của React hoặc Web API để xác minh; không tuyên bố đã tra cứu Context7. Skill review có template cho subagent; nếu công cụ tương ứng không có, báo giới hạn và tự review trong phạm vi được phép.

## Kiểm tra thay đổi

- Chạy các lệnh kiểm tra thực sự có trong dự án; không tự tạo hoặc tuyên bố đã chạy lệnh build/test chưa tồn tại.
- Khi có UI, kiểm tra luồng chính, trạng thái rỗng/chờ/lỗi, bàn phím và bố cục mobile theo checklist trong kế hoạch.
- Kiểm thử logic bằng JavaScript thuần và UI bằng checklist thủ công theo phạm vi hiện tại.
- Báo rõ những gì đã kiểm tra và phần còn chưa xác minh.
