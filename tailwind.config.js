// Sinh file docs/app.css từ các class Tailwind dùng trong docs/index.html.
// Sau khi sửa giao diện (thêm class mới) nhớ chạy lại:  npm install && npm run build:css
module.exports = {
  content: ['./docs/index.html'],
  theme: { extend: {} },
  plugins: []
};
