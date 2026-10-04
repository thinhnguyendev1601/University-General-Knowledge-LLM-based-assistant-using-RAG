# Skill Codex cho dự án

Bộ skill được sao chép từ các skill đã có trên máy vào `.agents/skills/`, giữ nguyên nội dung và các tệp hỗ trợ. Đây là hướng dẫn cho Codex, không phải dependency chạy trong ứng dụng.

| Skill | Mục đích | Nguồn cục bộ |
| --- | --- | --- |
| `coding-standards` | Chuẩn code và tổ chức JavaScript | `~/.codex/skills/coding-standards` |
| `frontend-patterns` | React, hooks, form, accessibility và hiệu năng | `~/.codex/skills/frontend-patterns` |
| `documentation-lookup` | Tra cứu tài liệu qua Context7 MCP | `~/.codex/skills/documentation-lookup` |
| `requesting-code-review` | Quy trình review và template cho reviewer | `~/.codex/skills/requesting-code-review` |

## Cách dùng

Ở lượt tiếp theo, yêu cầu Codex dùng skill theo tên, ví dụ:

- “Dùng $coding-standards và $frontend-patterns để triển khai màn hình login theo kế hoạch.”
- “Dùng $documentation-lookup để kiểm tra API React cần cho tính năng chat.”
- “Dùng $requesting-code-review để review tính năng vừa hoàn thành.”

Codex cũng có thể chọn skill theo mô tả khi công việc phù hợp. Nếu skill chưa xuất hiện, mở lại chat trong thư mục dự án.

`documentation-lookup` yêu cầu Context7 MCP với công cụ resolve-library-id và query-docs. Việc sao chép skill không cài hoặc cấu hình MCP; phiên cài đặt này chưa có công cụ Context7. `AGENTS.md` quy định dùng tài liệu chính thức làm phương án thay thế.

`requesting-code-review` đi kèm `code-reviewer.md` và có workflow dùng subagent. Dự án hiện chưa có Git hoặc mã nguồn; chỉ dùng bước lấy commit SHA khi repository thực sự tồn tại.

Tuân thủ stack React + JavaScript + CSS thuần trong `AGENTS.md` và kế hoạch. Các ví dụ của skill không mở rộng stack.

## Cập nhật

Đây là các bản sao độc lập, không tự đồng bộ với skill trên máy. Khi cập nhật, so sánh nội dung nguồn với bản trong dự án trước khi thay thế để bảo toàn tùy chỉnh.

Thư mục skill của repository tuân theo [tài liệu skill của OpenAI](https://developers.openai.com/codex/skills/).
