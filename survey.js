/* Bảng hỏi: Sự hài lòng với giải pháp thanh toán tự phục vụ
   Thang Likert 5 mức. Item gốc 7 mức đã chuyển về 5 mức (phải khai báo trong Methodology).
   Nguồn item gốc ghi ở trường `src` của mỗi khối. */

const LIKERT = [
  "Hoàn toàn không đồng ý",
  "Không đồng ý",
  "Trung lập",
  "Đồng ý",
  "Hoàn toàn đồng ý",
];

const SAT_ANCHORS = [
  ["SAT1", "Rất không hài lòng", "Rất hài lòng"],
  ["SAT2", "Rất khó chịu", "Rất dễ chịu"],
  ["SAT3", "Rất bực bội", "Rất thoải mái"],
  ["SAT4", "Rất tệ", "Rất tuyệt"],
];

const BLOCKS = [
  {
    id: "EFF",
    title: "Tính hiệu quả khi sử dụng",
    def: "Mức độ dễ dàng và nhanh chóng khi bạn tự thao tác thanh toán trên máy.",
    src: "SSTQUAL, Lin & Hsieh (2011), dimension Functionality",
    items: [
      ["EFF1", "Tôi hoàn tất được việc thanh toán tại máy tự phục vụ trong thời gian ngắn."],
      ["EFF2", "Quy trình thanh toán trên máy rõ ràng và dễ làm theo."],
      ["EFF3", "Việc sử dụng máy thanh toán tự phục vụ đòi hỏi rất ít công sức."],
      ["EFF4", "Tôi thao tác thanh toán trên máy một cách trôi chảy."],
    ],
  },
  {
    id: "REL",
    title: "Độ tin cậy của hệ thống",
    def: "Mức độ máy thanh toán hoạt động chính xác và không gây ra sai sót.",
    src: "Expected Reliability, Dabholkar (1996), chuyển từ semantic differential sang Likert",
    items: [
      ["REL1", "Máy tính đúng những món tôi thực sự mua."],
      ["REL2", "Tôi tin máy thanh toán tự phục vụ sẽ hoạt động tốt."],
      ["REL3", "Việc thanh toán tại máy diễn ra mà không có sai sót."],
      ["REL4", "Máy thanh toán tự phục vụ là thiết bị đáng tin cậy."],
    ],
  },
  {
    id: "SEC",
    title: "An toàn và bảo mật",
    def: "Mức độ bạn thấy thông tin và tiền của mình được bảo vệ khi giao dịch tại máy.",
    src: "SSTQUAL, Lin & Hsieh (2011), dimension Security/Privacy",
    items: [
      ["SEC1", "Tôi cảm thấy an toàn khi thực hiện giao dịch trên máy thanh toán tự phục vụ."],
      ["SEC2", "Thông tin cá nhân của tôi được giữ bí mật khi dùng máy."],
      ["SEC3", "Tôi thấy yên tâm khi cung cấp thông tin cần thiết cho máy."],
      ["SEC4", "Cửa hàng nêu rõ chính sách bảo mật khi tôi dùng máy thanh toán tự phục vụ."],
    ],
  },
  {
    id: "STF",
    title: "Sự hỗ trợ của nhân viên",
    def: "Mức độ sẵn có và hiệu quả của nhân viên cửa hàng khi bạn cần giúp đỡ tại khu vực tự thanh toán.",
    src: "e-SELFQUAL, Ding, Hu & Sheng (2011), dimension Customer Service (chuyển từ trực tuyến sang tại cửa hàng)",
    items: [
      ["STF1", "Tôi dễ dàng tìm được nhân viên hỗ trợ khi cần."],
      ["STF2", "Nhân viên thể hiện sự quan tâm thực sự đến việc giải quyết vấn đề của tôi."],
      ["STF3", "Nhân viên phản hồi nhanh khi tôi gặp trục trặc tại máy."],
    ],
  },
  {
    id: "PCT",
    title: "Cảm nhận về quyền kiểm soát",
    def: "Mức độ bạn thấy mình làm chủ quá trình thanh toán, thay vì bị động làm theo.",
    src: "Collier & Sherrell (2010), Perceived Control",
    items: [
      ["PCT1", "Tôi cảm thấy mình kiểm soát được quá trình thanh toán khi dùng máy."],
      ["PCT2", "Máy thanh toán tự phục vụ để cho khách hàng làm chủ giao dịch."],
      ["PCT3", "Khi dùng máy thanh toán, tôi cảm thấy mình chủ động quyết định."],
      ["PCT4", "Máy thanh toán tự phục vụ cho tôi nhiều quyền kiểm soát hơn đối với việc thanh toán."],
    ],
  },
  {
    id: "PRK",
    title: "Cảm nhận rủi ro sai sót thanh toán",
    def: "Mức độ bạn lo ngại máy có thể quét sai, tính sai hoặc gây thiệt hại về tiền.",
    src: "Featherman & Pavlou (2003), Performance risk + Financial risk",
    items: [
      ["PRK1", "Máy thanh toán tự phục vụ có thể hoạt động không đúng và gây rắc rối cho tôi."],
      ["PRK2", "Khả năng máy thanh toán gặp trục trặc hoặc chạy không đúng là điều có thật."],
      ["PRK3", "Xét theo mức độ hoạt động của máy, việc dùng nó để thanh toán là có rủi ro."],
      ["PRK4", "Tôi có nguy cơ bị mất tiền khi thanh toán tại máy tự phục vụ."],
      ["PRK5", "Thanh toán tại máy tự phục vụ khiến tiền của tôi có nguy cơ bị trừ sai."],
    ],
  },
  {
    id: "TAX",
    title: "Sự lo ngại công nghệ",
    def: "Phần này hỏi về cảm nhận CHUNG của bạn với công nghệ, không riêng máy thanh toán.",
    src: "Meuter, Ostrom, Bitner & Roundtree (2003), Technology Anxiety",
    items: [
      ["TAX1", "Tôi thấy khó hiểu phần lớn những vấn đề liên quan đến công nghệ."],
      ["TAX2", "Tôi thấy lo lắng khi phải sử dụng công nghệ."],
      ["TAX3", "Khi có cơ hội dùng công nghệ, tôi sợ mình có thể làm hỏng nó."],
      ["TAX4", "Tôi từng né tránh công nghệ vì thấy nó xa lạ với mình."],
    ],
  },
  {
    id: "CI",
    title: "Ý định tiếp tục sử dụng",
    def: "Dự định của bạn về việc dùng máy thanh toán tự phục vụ trong tương lai.",
    src: "Bhattacherjee (2001), IS Continuance Intention",
    items: [
      ["CI1", "Tôi dự định tiếp tục dùng máy thanh toán tự phục vụ thay vì ngừng sử dụng."],
      ["CI2", "Tôi có ý định dùng máy thanh toán tự phục vụ hơn là xếp hàng ở quầy có thu ngân."],
      ["CI3", "Nếu có thể, tôi muốn ngừng sử dụng máy thanh toán tự phục vụ.", { reverse: true }],
    ],
  },
  {
    id: "WOM",
    title: "Truyền miệng tích cực",
    def: "Mức độ bạn sẵn sàng nói tốt và giới thiệu máy thanh toán tự phục vụ cho người khác.",
    src: "Zeithaml, Berry & Parasuraman (1996), Behavioural Intentions Battery",
    items: [
      ["WOM1", "Tôi nói những điều tích cực về máy thanh toán tự phục vụ của cửa hàng này với người khác."],
      ["WOM2", "Tôi sẽ giới thiệu máy thanh toán tự phục vụ này cho người hỏi ý kiến tôi."],
      ["WOM3", "Tôi khuyến khích bạn bè và người thân sử dụng máy thanh toán tự phục vụ tại cửa hàng này."],
    ],
  },
];

/* Item kiểm soát chất lượng, chèn ngẫu nhiên vào khối chỉ định. expect = đáp án đúng.
   Nhóm 1: câu bẫy trực tiếp. */
const QC_ITEMS = [
  { code: "AC1", block: "SEC", expect: 2, tol: 0,
    text: "Đây là câu kiểm tra mức độ tập trung. Vui lòng chọn mức 2 (Không đồng ý)." },
  { code: "AC2", block: "PRK", expect: 4, tol: 0,
    text: "Để xác nhận bạn đang đọc kỹ từng câu, vui lòng chọn mức 4 (Đồng ý)." },
  { code: "BOG", block: "TAX", expect: 1, tol: 1,
    text: "Tôi chưa từng thực hiện bất kỳ giao dịch mua hàng nào trong đời." },

  /* Nhóm 2: cặp đồng nghĩa, đặt xa nhau, phải trả lời GẦN giống nhau.
     Chênh lệch lớn = đọc lướt hoặc điền ngẫu nhiên. */
  { code: "SYN1", block: "REL", pair: "SYN", role: "a",
    text: "Nhìn chung, máy thanh toán tự phục vụ dễ sử dụng đối với tôi." },
  { code: "SYN2", block: "WOM", pair: "SYN", role: "b",
    text: "Nói chung, việc dùng máy thanh toán tự phục vụ là đơn giản với tôi." },

  /* Nhóm 3: cặp trái nghĩa, phải trả lời NGƯỢC nhau.
     Trả lời cùng một mức = không đọc nội dung câu hỏi. */
  { code: "ANT1", block: "EFF", pair: "ANT", role: "a",
    text: "Tôi cảm thấy yên tâm khi để máy tự xử lý việc thanh toán của mình." },
  { code: "ANT2", block: "CI", pair: "ANT", role: "b",
    text: "Tôi cảm thấy bất an khi để máy tự xử lý việc thanh toán của mình." },
];

const DEMO = [
  { code: "gender", label: "Giới tính của bạn?",
    opts: ["Nam", "Nữ", "Khác", "Không muốn tiết lộ"] },
  { code: "age", label: "Độ tuổi của bạn?",
    opts: ["Dưới 18", "18-24", "25-34", "35-44", "45-54", "55 trở lên"] },
  { code: "edu", label: "Trình độ học vấn cao nhất của bạn?",
    opts: ["Trung học hoặc thấp hơn", "Trung cấp / Cao đẳng", "Đại học", "Sau đại học"] },
  { code: "freq", label: "Bạn dùng máy/quầy thanh toán tự phục vụ với tần suất nào?",
    opts: ["Hầu như mỗi lần mua sắm", "Vài lần một tuần", "Vài lần một tháng", "Hiếm khi"] },
  { code: "systype", label: "Loại hình thanh toán tự phục vụ bạn dùng NHIỀU NHẤT?",
    opts: ["Quầy bán tự động (nhân viên quét, khách tự trả tiền)",
           "Quầy tự thanh toán hoàn toàn (khách tự quét và tự trả)",
           "Kiosk tự gọi món và thanh toán",
           "Quét mã QR tại quầy"] },
  { code: "retailer", label: "Bạn thường dùng tại chuỗi nào nhất?",
    opts: ["AEON", "WinMart / WinMart+", "Uniqlo", "Decathlon",
           "Cửa hàng tiện lợi (Circle K, GS25, 7-Eleven…)", "Chuỗi đồ ăn nhanh", "Khác"] },
  { code: "spend", label: "Giá trị hoá đơn trung bình mỗi lần bạn thanh toán tại máy?",
    opts: ["Dưới 100.000đ", "100.000-300.000đ", "300.000-700.000đ", "Trên 700.000đ"] },
];

/* Biến phân nhóm cho PLS-MGA */
const ERROR_BLOCK = [
  { code: "err_exp", label: "Trong 6 THÁNG QUA, bạn có gặp sự cố nào khi thanh toán tại máy tự phục vụ không?",
    opts: ["Không, chưa gặp lần nào", "Có, đã gặp ít nhất một lần"] },
  { code: "err_type", label: "Nếu CÓ, đó là sự cố gì? (chọn nhiều được)", multi: true,
    showIf: "Có, đã gặp ít nhất một lần",
    opts: ["Máy quét sót món hàng", "Máy quét trùng, tính tiền 2 lần", "Trừ sai số tiền",
           "Giao dịch treo, phải làm lại", "Cổng an ninh báo động sai",
           "Không nhận được hoá đơn / biên lai", "Khác"] },
  { code: "err_fix", label: "Nếu CÓ, sự cố đó được xử lý thế nào?",
    showIf: "Có, đã gặp ít nhất một lần",
    opts: ["Được xử lý ngay tại chỗ, thoả đáng", "Được xử lý nhưng mất nhiều thời gian",
           "Không được xử lý thoả đáng", "Tôi bỏ qua, không báo ai"] },
];

const OPEN_QS = [
  { code: "open_good", label: "Điều bạn thấy HÀI LÒNG NHẤT khi thanh toán tại máy tự phục vụ là gì?" },
  { code: "open_bad", label: "Điều khiến bạn KHÓ CHỊU NHẤT (nếu có) là gì?" },
];
