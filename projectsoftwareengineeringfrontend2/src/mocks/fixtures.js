export const statuses = ['Đã gửi', 'Đang xử lý', 'Cần bổ sung', 'Đã giải quyết', 'Đã đóng'];
export const prompts = [
  { icon: 'spark', tone: 'blue', title: 'Hiểu một khái niệm', detail: 'Biến kiến thức khó thành điều dễ hiểu', question: 'Giải thích đạo hàm bằng một ví dụ đơn giản.' },
  { icon: 'pen', tone: 'green', title: 'Cùng giải bài tập', detail: 'Từng bước, để bạn thực sự hiểu', question: 'Hướng dẫn từng bước tính đạo hàm của f(x) = x².' },
  { icon: 'book', tone: 'violet', title: 'Khám phá tài liệu', detail: 'Tìm ý chính và nguồn tham khảo', question: 'Tóm tắt nội dung chính trong tài liệu Calculus 1 mẫu.' },
  { icon: 'cap', tone: 'amber', title: 'Chuyện học ở IU', detail: 'Gợi ý để việc học nhẹ nhàng hơn', question: 'Làm thế nào để xây dựng kế hoạch ôn tập hiệu quả?' }
];
const source = { id: 'calculus-1', documentTitle: 'Calculus 1 · Derivatives', course: 'Calculus 1', page: 24, section: '2.1 — The derivative', excerpt: 'Đạo hàm biểu diễn tốc độ thay đổi tức thời của hàm số. Với f(x) = x², f′(x) = 2x. Tại x = 3, hệ số góc của tiếp tuyến bằng 6. Đây là đoạn trích minh họa được biên soạn cho bản demo, không phải tài liệu chính thức.' };
export function responseFor(question) {
  const normalized = question.toLowerCase();
  if (/code|javascript|lập trình/.test(normalized)) return { blocks: [{ type: 'paragraph', text: 'Ví dụ JavaScript đơn giản: tính bình phương một số.' }, { type: 'code', text: 'function square(number) {\n  return number * number;\n}\n\nconsole.log(square(3)); // 9' }], citations: [] };
  if (/đạo hàm|calculus|tài liệu/.test(normalized)) return { blocks: [
    { type: 'paragraph', text: 'Đạo hàm cho biết một đại lượng thay đổi nhanh đến mức nào tại một thời điểm. Bạn có thể nghĩ đến vận tốc: vị trí là hàm số, còn vận tốc là đạo hàm của vị trí. [1]' },
    { type: 'heading', text: 'Thử với một ví dụ nhỏ' },
    { type: 'list', items: ['Xét hàm số f(x) = x².', 'Áp dụng quy tắc lũy thừa: f′(x) = 2x.', 'Tại x = 3, ta có f′(3) = 6: tiếp tuyến có hệ số góc bằng 6.'] },
    { type: 'table', headers: ['Giá trị x', 'f(x) = x²', 'f′(x) = 2x'], rows: [['1', '1', '2'], ['2', '4', '4'], ['3', '9', '6']] },
    { type: 'paragraph', text: 'Hãy thử tính tại x = 5 để kiểm tra bạn đã hiểu quy tắc nhé. Đây là câu trả lời mẫu phục vụ trải nghiệm giao diện.' }
  ], citations: [source] };
  return { blocks: [{ type: 'paragraph', text: 'Bạn có thể bắt đầu bằng cách chia mục tiêu học tập thành những phần nhỏ, rõ ràng. Đây là gợi ý tổng quát được mô phỏng trong bản demo.' }, { type: 'heading', text: 'Một cách bắt đầu nhẹ nhàng' }, { type: 'list', items: ['Chọn một chủ đề và viết ra điều bạn chưa hiểu.', 'Dành 25 phút đọc và thử một bài tập nhỏ.', 'Ghi lại kết quả, nghỉ ngắn và ôn lại vào ngày tiếp theo.'] }, { type: 'paragraph', text: 'Nếu bạn cần kiểm tra một quy định của IU, hãy tham khảo kênh thông tin chính thức. Bản demo chưa truy xuất tài liệu thật.' }], citations: [] };
}
export function createFixtures() {
  const now = Date.now();
  const titles = ['Đạo hàm và tốc độ thay đổi', 'Lập kế hoạch ôn tập giữa kỳ', 'Tóm tắt tài liệu Calculus 1', 'Giải bài tập hàm số', 'JavaScript: hàm và biến', 'Cách ghi chú bài giảng hiệu quả', 'Nguồn tham khảo cho bài tập nhóm', 'Chuẩn bị cho một học kỳ mới'];
  const conversations = titles.map((title, index) => {
    const createdAt = new Date(now - [0, 0, 1, 2, 3, 6, 9, 14][index] * 86400000).toISOString();
    const question = index === 0 ? prompts[0].question : title;
    const answer = responseFor(question);
    return { id: `sample-chat-${index + 1}`, title, createdAt, updatedAt: createdAt, messages: [{ id: `q-${index}`, role: 'user', content: question, status: 'complete', createdAt }, { id: `a-${index}`, role: 'assistant', content: answer.blocks, citations: answer.citations, status: 'complete', feedback: null, createdAt }] };
  });
  const tickets = ['Cần giải thích rõ hơn về quy tắc đạo hàm', 'Kiểm tra nguồn tài liệu tham khảo', 'Góp ý về giao diện trên điện thoại', 'Câu hỏi về bài tập Calculus 1', 'Nguồn mẫu chưa đủ thông tin', 'Gợi ý cải thiện cách trình bày'].map((title, index) => {
    const createdAt = new Date(now - index * 86400000).toISOString();
    const status = statuses[index % statuses.length];
    return { id: `IU-${1006 - index}`, title, category: ['Nội dung trả lời', 'Nguồn tài liệu', 'Vấn đề giao diện'][index % 3], course: 'Calculus 1 (mẫu)', description: 'Tôi muốn được giải thích chi tiết hơn để hiểu nội dung này. Đây là ticket mẫu, chưa gửi đến nhân viên IU.', status, createdAt, conversationId: index === 0 ? conversations[0].id : null, selectedExcerpt: index === 0 ? 'Với f(x) = x², đạo hàm là f′(x) = 2x.' : '', timeline: [{ status: 'Đã gửi', date: createdAt, note: 'Ticket mẫu đã được tạo.' }, ...(status !== 'Đã gửi' ? [{ status, date: createdAt, note: status === 'Cần bổ sung' ? 'Cần nêu rõ trang tài liệu hoặc bước giải bạn đang gặp khó khăn. Tính năng bổ sung sẽ có ở phiên bản sau.' : 'Trạng thái mô phỏng cho bản demo.' }] : [])] };
  });
  return { conversations, tickets };
}
