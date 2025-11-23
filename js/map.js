// Khởi tạo bản đồ ở hệ tọa độ pixel của ảnh quy hoạch và dùng JPG làm nền (image overlay)
const map = L.map("map", {
  crs: L.CRS.Simple,
  zoomControl: true,
  minZoom: -2,
  maxZoom: 4,
});

// Sử dụng ảnh quy hoạch trong thư mục assets
const imageUrl = "assets/z7252001718473_79a63f05e18674f84b46ce6d1693b223.jpg";

// Đọc kích thước thực của ảnh để bounds khít 100% với bản vẽ
const img = new Image();
img.onload = () => {
  const IMAGE_WIDTH = img.naturalWidth;
  const IMAGE_HEIGHT = img.naturalHeight;

  // Bounds của image overlay dùng [lat, lng] = [y, x] tính từ góc trên-trái (0,0)
  const imageBounds = [
    [0, 0], // góc trên-trái
    [IMAGE_HEIGHT, IMAGE_WIDTH], // góc dưới-phải (maxY, maxX)
  ];

  L.imageOverlay(imageUrl, imageBounds).addTo(map);
  map.fitBounds(imageBounds);

  // Tải dữ liệu GeoJSON từ file sau khi biết kích thước ảnh
  fetch("data/map.geojson")
    .then((res) => res.json())
    .then((geojson) => {
      L.geoJSON(geojson, {
        // Chuyển toạ độ [x, y] từ image-map sang [lat, lng] của Leaflet.
        // Đảo trục Y để khớp hệ toạ độ ảnh, giữ nguyên trục X để tránh lật ngang.
        coordsToLatLng: (coords) => {
          const [x, y] = coords;
          const ny = IMAGE_HEIGHT - y;
          return L.latLng(ny, x);
        },
        // Tuỳ biến hiển thị cho các điểm (intersection / exit)
        pointToLayer: (feature, latlng) => {
          const props = feature.properties || {};
          const type = props.type;

          if (type === "intersection") {
            const isExit = props.is_exit;
            return L.circleMarker(latlng, {
              radius: isExit ? 5 : 4,
              color: isExit ? "#ff0000" : "#ffffff",
              fillColor: isExit ? "#ff4444" : "#ffcc00",
              fillOpacity: 0.9,
              weight: 1,
            });
          }

          return L.circleMarker(latlng, {
            radius: 3,
            color: "#ffffff",
            weight: 1,
            fillOpacity: 0,
          });
        },
        style: (feature) => {
          const type = feature.properties.type;

          if (type === "zone") {
            const risk = feature.properties.flood_risk;
            let fillColor = "#91cf60";
            if (risk === "very_low") fillColor = "#1a9850";
            else if (risk === "low") fillColor = "#91cf60";
            else if (risk === "medium") fillColor = "#fee08b";
            else if (risk === "high") fillColor = "#fc8d59";

            return {
              color: "#ffffff",
              weight: 1.2,
              fillColor,
              fillOpacity: 0.7,
            };
          }

          if (type === "river") {
            return {
              color: "#2980b9",
              weight: 4,
            };
          }

          if (type === "road") {
            return {
              color: "#ffcc00",
              weight: 2.5,
            };
          }

          return {
            color: "#ffffff",
            weight: 1,
          };
        },
        onEachFeature: (feature, layer) => {
          const props = feature.properties || {};
          const type = props.type;

          if (type === "zone") {
            const riskLabelMap = {
              very_low: "Rất thấp",
              low: "Thấp",
              medium: "Trung bình",
              high: "Cao",
            };

            const html = `
                  <b>${props.name || "Khu vực"}</b><br/>
                  Độ cao: <b>${props.elevation_label || "N/A"}</b><br/>
                  Rủi ro ngập: <b>${
                    riskLabelMap[props.flood_risk] || "Không xác định"
                  }</b><br/>
                  Ghi chú: ${props.description || "—"}
                `;
            layer.bindTooltip(html, { sticky: true });
          } else if (type === "river") {
            const html = `
                  <b>${props.name || "Sông"}</b><br/>
                  Vai trò: Nguồn nước dâng gây lũ<br/>
                  Hướng chảy: ${props.flow_direction || "Bắc - Nam"}
                `;
            layer.bindTooltip(html, { sticky: true });
          } else if (type === "road") {
            const html = `
                  <b>${props.name || "Đường giao thông"}</b><br/>
                  Loại: ${props.level || "chưa xác định"}<br/>
                  Ghi chú: ${props.description || "—"}
                `;
            layer.bindTooltip(html, { sticky: true });
          } else if (type === "intersection") {
            const html = `
                  <b>Nút giao đường</b><br/>
                  Bậc giao: ${props.degree || 1}<br/>
                  Lối thoát: ${
                    props.is_exit
                      ? props.exit_side || "Có (gần biên bản đồ)"
                      : "Không"
                  }
                `;
            layer.bindTooltip(html, { sticky: true });
          }
        },
      }).addTo(map);
    })
    .catch((err) => {
      console.error("Không thể tải dữ liệu bản đồ:", err);
    });
};

img.src = imageUrl;


