const crypto = require('crypto');
const { Resvg } = require('@resvg/resvg-js');

/**
 * Thư viện Vector Art Deco tạo hình đối tượng nhận diện rõ ràng 100%
 * "con heo ra con heo, cái bàn ra cái bàn"
 * Chuẩn màu Art Deco: Cream #F4EAD5, Gold #C9A227, Black #18181B, Teal #1E6E6B
 */

function generateArtDecoSvg(prompt) {
  const p = prompt.toLowerCase().trim();
  const hash = crypto.createHash('sha256').update(p).digest();

  // Xác định đối tượng và tạo SVG chi tiết
  let subjectSvg = '';

  // 1. CON HEO / PIG
  if (/pig|heo|lợn|swine/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Pig (Con Heo) -->
      <ellipse cx="132" cy="136" rx="56" ry="42" fill="#F4A6BC" stroke="#C9A227" stroke-width="2.5"/>
      <ellipse cx="132" cy="146" rx="42" ry="25" fill="#FAD1DC"/>
      <circle cx="86" cy="120" r="32" fill="#F4A6BC" stroke="#C9A227" stroke-width="2.5"/>
      <!-- Tai heo hình tam giác cụp -->
      <polygon points="66,96 82,78 92,98" fill="#DF84A0" stroke="#C9A227" stroke-width="2"/>
      <polygon points="96,94 112,80 118,100" fill="#DF84A0" stroke="#C9A227" stroke-width="2"/>
      <!-- Mũi heo to tròn với 2 lỗ mũi đặc trưng -->
      <ellipse cx="68" cy="126" rx="16" ry="12" fill="#FAD1DC" stroke="#C9A227" stroke-width="2"/>
      <ellipse cx="63" cy="126" rx="3.5" ry="5.5" fill="#882D46"/>
      <ellipse cx="73" cy="126" rx="3.5" ry="5.5" fill="#882D46"/>
      <!-- Mắt đen có tròng trắng -->
      <circle cx="86" cy="112" r="5" fill="#18181B"/>
      <circle cx="88" cy="110.5" r="1.5" fill="#FFFFFF"/>
      <!-- 4 Chân có móng heo -->
      <rect x="102" y="170" width="12" height="22" rx="3" fill="#F4A6BC" stroke="#C9A227" stroke-width="1.5"/>
      <polygon points="102,188 108,192 114,188" fill="#18181B"/>
      <rect x="124" y="170" width="12" height="22" rx="3" fill="#F4A6BC" stroke="#C9A227" stroke-width="1.5"/>
      <polygon points="124,188 130,192 136,188" fill="#18181B"/>
      <rect x="148" y="168" width="12" height="22" rx="3" fill="#F4A6BC" stroke="#C9A227" stroke-width="1.5"/>
      <polygon points="148,186 154,190 160,186" fill="#18181B"/>
      <!-- Đuôi xoắn ốc đáng yêu -->
      <path d="M 188 130 Q 200 124 198 114 Q 194 106 204 110 Q 208 116 202 124" fill="none" stroke="#F4A6BC" stroke-width="4.5" stroke-linecap="round"/>
    `;
  }
  // 2. CÁI BÀN / TABLE
  else if (/table|bàn|desk/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Table (Cái Bàn) -->
      <!-- Mặt bàn 3D phối cảnh chuẩn -->
      <polygon points="42,120 214,120 186,90 70,90" fill="#C9A227" stroke="#18181B" stroke-width="2"/>
      <polygon points="42,120 214,120 214,129 42,129" fill="#967117" stroke="#18181B" stroke-width="2"/>
      <polygon points="214,120 186,90 186,97 214,129" fill="#78550E" stroke="#18181B" stroke-width="1.5"/>
      <!-- Khăn trải bàn trung tâm màu Teal Art Deco -->
      <polygon points="110,90 146,90 155,120 101,120" fill="#1E6E6B" opacity="0.95"/>
      <!-- 4 Chân bàn vững chắc có chân bọc đồng vàng -->
      <polygon points="54,129 60,129 58,192 52,192" fill="#2D2006" stroke="#C9A227" stroke-width="1.5"/>
      <rect x="50" y="192" width="10" height="6" fill="#C9A227"/>
      <polygon points="196,129 202,129 200,192 194,192" fill="#2D2006" stroke="#C9A227" stroke-width="1.5"/>
      <rect x="192" y="192" width="10" height="6" fill="#C9A227"/>
      <polygon points="76,106 81,106 79,166 74,166" fill="#18181B" stroke="#967117" stroke-width="1.5"/>
      <rect x="73" y="166" width="8" height="5" fill="#C9A227"/>
      <polygon points="174,106 179,106 177,166 172,166" fill="#18181B" stroke="#967117" stroke-width="1.5"/>
      <rect x="171" y="166" width="8" height="5" fill="#C9A227"/>
      <!-- Khung giằng chân bàn -->
      <line x1="56" y1="162" x2="198" y2="162" stroke="#C9A227" stroke-width="2.5"/>
    `;
  }
  // 3. CON CHÓ / DOG
  else if (/dog|chó|puppy|hound/i.test(p)) {
    const isBlack = p.includes('black');
    const furColor = isBlack ? '#18181B' : '#A76D28';
    const earColor = isBlack ? '#27272A' : '#784714';
    subjectSvg = `
      <!-- Art Deco Dog (Con Chó) -->
      <!-- Thân ngồi vững vàng -->
      <ellipse cx="140" cy="144" rx="46" ry="34" fill="${furColor}" stroke="#C9A227" stroke-width="2"/>
      <!-- Đầu chó và mõm dài -->
      <circle cx="86" cy="110" r="26" fill="${furColor}" stroke="#C9A227" stroke-width="2"/>
      <!-- Mõm chó -->
      <polygon points="62,112 84,102 84,124 64,122" fill="${furColor}" stroke="#C9A227" stroke-width="1.5"/>
      <circle cx="62" cy="116" r="4.5" fill="#000000"/>
      <!-- Tai chó rủ -->
      <polygon points="90,92 108,98 104,130 88,114" fill="${earColor}" stroke="#C9A227" stroke-width="2"/>
      <!-- Mắt chó trung thành -->
      <circle cx="82" cy="106" r="4" fill="#C9A227"/>
      <circle cx="82" cy="106" r="2.5" fill="#000000"/>
      <!-- Vòng cổ vàng Art Deco -->
      <path d="M 82 128 Q 98 136 108 126" stroke="#C9A227" stroke-width="5" fill="none"/>
      <circle cx="95" cy="135" r="4" fill="#C9A227"/>
      <!-- Chân trước & chân sau -->
      <rect x="76" y="142" width="12" height="42" rx="4" fill="${furColor}" stroke="#C9A227" stroke-width="1.5"/>
      <rect x="94" y="142" width="12" height="42" rx="4" fill="${furColor}" stroke="#C9A227" stroke-width="1.5"/>
      <ellipse cx="160" cy="162" rx="18" ry="16" fill="${earColor}"/>
      <!-- Đuôi chó vểnh mừng -->
      <path d="M 182 144 Q 206 136 210 114" fill="none" stroke="${furColor}" stroke-width="7" stroke-linecap="round"/>
    `;
  }
  // 4. CON MÈO / CAT
  else if (/cat|mèo|kitten|feline/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Cat (Con Mèo) -->
      <ellipse cx="130" cy="148" rx="42" ry="32" fill="#18181B" stroke="#C9A227" stroke-width="2"/>
      <circle cx="100" cy="114" r="24" fill="#18181B" stroke="#C9A227" stroke-width="2"/>
      <!-- Tai mèo nhọn đặc trưng -->
      <polygon points="84,98 94,76 102,96" fill="#18181B" stroke="#C9A227" stroke-width="2"/>
      <polygon points="88,96 94,82 98,96" fill="#EFA2B8"/>
      <polygon points="106,96 116,76 124,98" fill="#18181B" stroke="#C9A227" stroke-width="2"/>
      <polygon points="110,96 116,82 120,96" fill="#EFA2B8"/>
      <!-- Mắt mèo ngọc bích -->
      <ellipse cx="92" cy="112" rx="4.5" ry="6" fill="#10B981"/>
      <ellipse cx="92" cy="112" rx="1.5" ry="5.5" fill="#000000"/>
      <ellipse cx="108" cy="112" rx="4.5" ry="6" fill="#10B981"/>
      <ellipse cx="108" cy="112" rx="1.5" ry="5.5" fill="#000000"/>
      <!-- Mũi hồng và râu mèo -->
      <polygon points="98,118 102,118 100,121" fill="#EFA2B8"/>
      <line x1="84" y1="120" x2="62" y2="116" stroke="#C9A227" stroke-width="1.5"/>
      <line x1="84" y1="122" x2="62" y2="124" stroke="#C9A227" stroke-width="1.5"/>
      <line x1="116" y1="120" x2="138" y2="116" stroke="#C9A227" stroke-width="1.5"/>
      <line x1="116" y1="122" x2="138" y2="124" stroke="#C9A227" stroke-width="1.5"/>
      <!-- Chân trước xếp ngay ngắn -->
      <rect x="90" y="146" width="10" height="38" rx="4" fill="#18181B" stroke="#C9A227" stroke-width="1.5"/>
      <rect x="104" y="146" width="10" height="38" rx="4" fill="#18181B" stroke="#C9A227" stroke-width="1.5"/>
      <!-- Đuôi mèo uốn cong duyên dáng -->
      <path d="M 168 152 Q 198 162 196 130 Q 194 116 182 112" fill="none" stroke="#18181B" stroke-width="6" stroke-linecap="round"/>
    `;
  }
  // 5. CHIẾC XE / CAR
  else if (/car|xe|automobile|vehicle/i.test(p)) {
    const isBlue = p.includes('blue');
    const carColor = isBlue ? '#1E6E6B' : (p.includes('red') ? '#B91C1C' : '#C9A227');
    subjectSvg = `
      <!-- Art Deco Roadster Car (Chiếc Xe) -->
      <!-- Thân xe khí động học 1930s -->
      <path d="M 40 152 C 55 125, 110 115, 160 115 C 195 115, 218 135, 224 152 Z" fill="${carColor}" stroke="#18181B" stroke-width="2.5"/>
      <!-- Kính chắn gió mạ vàng -->
      <polygon points="120,116 142,100 158,116" fill="#F4EAD5" stroke="#C9A227" stroke-width="2"/>
      <!-- Khung gầm mạ kim loại -->
      <rect x="36" y="150" width="188" height="15" rx="3" fill="#18181B" stroke="#C9A227" stroke-width="2"/>
      <!-- Đèn pha tròn mạ vàng Art Deco -->
      <circle cx="218" cy="144" r="8" fill="#F4EAD5" stroke="#C9A227" stroke-width="2"/>
      <circle cx="218" cy="144" r="5" fill="#FFE899"/>
      <!-- Bánh xe trước & sau với nan hoa vàng -->
      <circle cx="78" cy="165" r="22" fill="#18181B" stroke="#C9A227" stroke-width="3"/>
      <circle cx="78" cy="165" r="12" fill="#967117"/>
      <circle cx="78" cy="165" r="5" fill="#C9A227"/>
      <circle cx="178" cy="165" r="22" fill="#18181B" stroke="#C9A227" stroke-width="3"/>
      <circle cx="178" cy="165" r="12" fill="#967117"/>
      <circle cx="178" cy="165" r="5" fill="#C9A227"/>
    `;
  }
  // 6. CÁI CÂY / TREE
  else if (/tree|cây|forest|redwood/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Tree (Cái Cây) -->
      <!-- Gốc và thân cây vươn thẳng -->
      <polygon points="120,195 136,195 132,130 124,130" fill="#78350F" stroke="#C9A227" stroke-width="2"/>
      <line x1="110" y1="195" x2="146" y2="195" stroke="#C9A227" stroke-width="3"/>
      <!-- Tán lá Art Deco xếp tầng rẻ quạt -->
      <polygon points="128,70 82,120 174,120" fill="#1E6E6B" stroke="#C9A227" stroke-width="2"/>
      <polygon points="128,95 72,145 184,145" fill="#166534" stroke="#C9A227" stroke-width="2"/>
      <polygon points="128,120 62,175 194,175" fill="#14532D" stroke="#C9A227" stroke-width="2"/>
      <!-- Ngôi sao / trái vàng trên tán cây -->
      <circle cx="128" cy="68" r="6" fill="#C9A227"/>
    `;
  }
  // 7. HOA / FLOWER / ROSE / SUNFLOWER
  else if (/flower|rose|sunflower|hoa/i.test(p)) {
    const isSunflower = p.includes('sunflower') || p.includes('hướng dương');
    const petalColor = isSunflower ? '#EAB308' : '#DC2626';
    subjectSvg = `
      <!-- Art Deco Flower (Bông Hoa) -->
      <!-- Cuống hoa & lá đối xứng -->
      <line x1="128" y1="130" x2="128" y2="195" stroke="#1E6E6B" stroke-width="5"/>
      <ellipse cx="106" cy="165" rx="20" ry="8" transform="rotate(-25 106 165)" fill="#1E6E6B" stroke="#C9A227" stroke-width="1.5"/>
      <ellipse cx="150" cy="155" rx="20" ry="8" transform="rotate(25 150 155)" fill="#1E6E6B" stroke="#C9A227" stroke-width="1.5"/>
      <!-- Các cánh hoa tỏa tròn Art Deco -->
      <circle cx="128" cy="115" r="48" fill="${petalColor}" stroke="#C9A227" stroke-width="2.5"/>
      <circle cx="128" cy="115" r="36" fill="${isSunflower ? '#CA8A04' : '#B91C1C'}" stroke="#C9A227" stroke-width="2"/>
      <circle cx="128" cy="115" r="22" fill="#78350F" stroke="#C9A227" stroke-width="2"/>
      <!-- Tâm hoa vàng óng -->
      <circle cx="128" cy="115" r="10" fill="#C9A227"/>
    `;
  }
  // 8. CON VOI / ELEPHANT
  else if (/elephant|voi/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Elephant (Con Voi) -->
      <!-- Thân đồ sộ -->
      <ellipse cx="145" cy="138" rx="55" ry="42" fill="#64748B" stroke="#C9A227" stroke-width="2"/>
      <!-- Đầu và tai to -->
      <circle cx="95" cy="120" r="28" fill="#64748B" stroke="#C9A227" stroke-width="2"/>
      <ellipse cx="112" cy="122" rx="18" ry="24" fill="#475569" stroke="#C9A227" stroke-width="2"/>
      <!-- Vòi voi uốn cong kiêu hãnh -->
      <path d="M 80 126 C 65 145, 52 165, 50 150 C 48 135, 60 126, 68 116" fill="none" stroke="#64748B" stroke-width="8" stroke-linecap="round"/>
      <!-- Ngà voi trắng cong nhọn -->
      <path d="M 78 132 Q 62 142 56 130" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round"/>
      <!-- 4 Chân hình trụ khỏe khoắn -->
      <rect x="105" y="165" width="16" height="30" fill="#64748B" stroke="#C9A227" stroke-width="1.5"/>
      <rect x="128" y="165" width="16" height="30" fill="#64748B" stroke="#C9A227" stroke-width="1.5"/>
      <rect x="156" y="165" width="16" height="30" fill="#64748B" stroke="#C9A227" stroke-width="1.5"/>
    `;
  }
  // 9. CÁI GHẾ / CHAIR
  else if (/chair|ghế/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Chair (Cái Ghế) -->
      <!-- Lưng ghế vòm Art Deco -->
      <path d="M 88 135 C 88 80, 168 80, 168 135 Z" fill="#1E6E6B" stroke="#C9A227" stroke-width="2.5"/>
      <path d="M 100 135 C 100 95, 156 95, 156 135 Z" fill="#14532D" stroke="#C9A227" stroke-width="1.5"/>
      <!-- Đệm ngồi bọc nhung -->
      <polygon points="76,145 180,145 170,135 86,135" fill="#C9A227" stroke="#18181B" stroke-width="2"/>
      <rect x="76" y="145" width="104" height="12" rx="3" fill="#967117" stroke="#18181B" stroke-width="1.5"/>
      <!-- 4 Chân ghế thanh thoát -->
      <line x1="86" y1="157" x2="78" y2="198" stroke="#2D2006" stroke-width="4"/>
      <circle cx="78" cy="198" r="3.5" fill="#C9A227"/>
      <line x1="170" y1="157" x2="178" y2="198" stroke="#2D2006" stroke-width="4"/>
      <circle cx="178" cy="198" r="3.5" fill="#C9A227"/>
      <line x1="102" y1="157" x2="98" y2="185" stroke="#18181B" stroke-width="3"/>
      <line x1="154" y1="157" x2="158" y2="185" stroke="#18181B" stroke-width="3"/>
    `;
  }
  // 10. QUẢ TÁO / APPLE
  else if (/apple|táo|fruit/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Apple (Quả Táo) -->
      <!-- Thân quả táo đỏ rực có vết lõm chuẩn -->
      <path d="M 128 100 C 100 75, 68 105, 78 140 C 88 175, 115 185, 128 180 C 141 185, 168 175, 178 140 C 188 105, 156 75, 128 100 Z" fill="#DC2626" stroke="#C9A227" stroke-width="2.5"/>
      <!-- Vết sáng bóng Art Deco -->
      <path d="M 92 115 C 88 130, 92 150, 102 160" fill="none" stroke="#FCA5A5" stroke-width="4" stroke-linecap="round"/>
      <!-- Cuống táo & lá xanh nghiêng -->
      <path d="M 128 100 Q 135 80 142 75" fill="none" stroke="#78350F" stroke-width="4" stroke-linecap="round"/>
      <ellipse cx="146" cy="84" rx="14" ry="7" transform="rotate(-30 146 84)" fill="#15803D" stroke="#C9A227" stroke-width="1.5"/>
    `;
  }
  // 11. CÁI MŨ / NÓN / HAT
  else if (/hat|mũ|nón|cap/i.test(p)) {
    const isRed = p.includes('red');
    const hatColor = isRed ? '#B91C1C' : '#18181B';
    subjectSvg = `
      <!-- Art Deco Fedora Hat (Cái Mũ) -->
      <!-- Chóp mũ cong lõm chuẩn phong cách -->
      <path d="M 88 135 C 88 95, 105 85, 128 92 C 151 85, 168 95, 168 135 Z" fill="${hatColor}" stroke="#C9A227" stroke-width="2.5"/>
      <!-- Dải ruy băng vàng Art Deco quấn quanh nón -->
      <rect x="87" y="125" width="82" height="10" fill="#C9A227" stroke="#18181B" stroke-width="1.5"/>
      <!-- Vành nón uốn cong thanh lịch -->
      <ellipse cx="128" cy="142" rx="72" ry="16" fill="${hatColor}" stroke="#C9A227" stroke-width="2.5"/>
      <ellipse cx="128" cy="142" rx="55" ry="10" fill="none" stroke="#967117" stroke-width="1.5"/>
    `;
  }
  // 12. HÀNH TINH / SAO THỔ / SOLAR SYSTEM
  else if (/saturn|planet|solar|hành tinh|vũ trụ/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Saturn / Planet -->
      <!-- Quả cầu hành tinh với các dải sọc bão -->
      <circle cx="128" cy="128" r="46" fill="#C9A227" stroke="#18181B" stroke-width="2"/>
      <path d="M 82 120 C 105 130, 151 130, 174 120" stroke="#78350F" stroke-width="5" fill="none"/>
      <path d="M 86 135 C 108 145, 148 145, 170 135" stroke="#1E6E6B" stroke-width="4" fill="none"/>
      <!-- Vành đai elip nghiêng Art Deco -->
      <ellipse cx="128" cy="128" rx="88" ry="24" transform="rotate(-18 128 128)" fill="none" stroke="#C9A227" stroke-width="6"/>
      <ellipse cx="128" cy="128" rx="76" ry="18" transform="rotate(-18 128 128)" fill="none" stroke="#F4EAD5" stroke-width="2"/>
      <!-- Nửa vành đai phía trước che một phần quả cầu -->
      <path d="M 44 145 C 80 185, 180 155, 212 110" transform="rotate(-18 128 128)" stroke="#C9A227" stroke-width="6" fill="none"/>
    `;
  }
  // 13. NGÔI NHÀ / HOUSE
  else if (/house|nhà|building/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco House (Ngôi Nhà) -->
      <!-- Thân nhà chính -->
      <rect x="76" y="118" width="104" height="74" fill="#F4EAD5" stroke="#C9A227" stroke-width="2.5"/>
      <!-- Mái nhà tam giác Art Deco -->
      <polygon points="64,120 128,68 192,120" fill="#78350F" stroke="#C9A227" stroke-width="2.5"/>
      <!-- Ống khói -->
      <rect x="156" y="78" width="14" height="26" fill="#18181B" stroke="#C9A227" stroke-width="1.5"/>
      <!-- Cửa chính vòm mạ vàng -->
      <path d="M 114 192 L 114 150 C 114 140, 142 140, 142 150 L 142 192 Z" fill="#1E6E6B" stroke="#C9A227" stroke-width="2"/>
      <circle cx="136" cy="168" r="2.5" fill="#C9A227"/>
      <!-- Cửa sổ vuông đối xứng -->
      <rect x="88" y="136" width="18" height="18" fill="#FDE68A" stroke="#18181B" stroke-width="1.5"/>
      <line x1="97" y1="136" x2="97" y2="154" stroke="#18181B" stroke-width="1"/>
      <line x1="88" y1="145" x2="106" y2="145" stroke="#18181B" stroke-width="1"/>
      <rect x="150" y="136" width="18" height="18" fill="#FDE68A" stroke="#18181B" stroke-width="1.5"/>
      <line x1="159" y1="136" x2="159" y2="154" stroke="#18181B" stroke-width="1"/>
      <line x1="150" y1="145" x2="168" y2="145" stroke="#18181B" stroke-width="1"/>
    `;
  }
  // 14. CHIM / ĐẠI BÀNG / BIRD / EAGLE
  else if (/bird|eagle|chim|đại bàng|falcon|swan/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Eagle (Đại Bàng) -->
      <!-- Đôi cánh Art Deco xòe rộng hình quạt -->
      <polygon points="128,125 45,85 85,145" fill="#18181B" stroke="#C9A227" stroke-width="2"/>
      <polygon points="128,125 211,85 171,145" fill="#18181B" stroke="#C9A227" stroke-width="2"/>
      <!-- Thân và ngực chim kiêu hãnh -->
      <ellipse cx="128" cy="140" rx="20" ry="32" fill="#78350F" stroke="#C9A227" stroke-width="2"/>
      <!-- Đầu và mỏ khoằm dũng mãnh -->
      <circle cx="128" cy="100" r="16" fill="#F4EAD5" stroke="#C9A227" stroke-width="2"/>
      <polygon points="128,98 148,106 128,112" fill="#C9A227" stroke="#18181B" stroke-width="1.5"/>
      <circle cx="124" cy="98" r="3" fill="#18181B"/>
      <!-- Đuôi xòe & móng vuốt đậu trên cành vàng -->
      <polygon points="120,170 128,192 136,170" fill="#18181B"/>
      <line x1="90" y1="185" x2="166" y2="185" stroke="#C9A227" stroke-width="3"/>
    `;
  }
  // 15. THUYỀN / BOAT / SHIP
  else if (/boat|ship|thuyền|tàu/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Sailboat (Thuyền Buồm) -->
      <!-- Thân thuyền rẽ sóng -->
      <polygon points="56,160 196,160 178,180 82,180" fill="#78350F" stroke="#C9A227" stroke-width="2.5"/>
      <line x1="50" y1="182" x2="206" y2="182" stroke="#1E6E6B" stroke-width="3"/>
      <!-- Cột buồm thẳng đứng -->
      <line x1="130" y1="65" x2="130" y2="160" stroke="#C9A227" stroke-width="3"/>
      <!-- Cánh buồm tam giác căng gió -->
      <polygon points="130,70 185,148 130,148" fill="#F4EAD5" stroke="#C9A227" stroke-width="2.5"/>
      <polygon points="126,82 78,148 126,148" fill="#C9A227" stroke="#18181B" stroke-width="2"/>
    `;
  }
  // 16. MÁY BAY / AIRPLANE
  else if (/airplane|plane|máy bay/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Airplane -->
      <polygon points="128,60 134,165 128,175 122,165" fill="#18181B" stroke="#C9A227" stroke-width="2"/>
      <polygon points="55,130 128,110 201,130 188,142 128,128 68,142" fill="#C9A227" stroke="#18181B" stroke-width="2"/>
      <polygon points="106,172 128,162 150,172 144,180 128,174 112,180" fill="#1E6E6B" stroke="#C9A227" stroke-width="1.5"/>
      <circle cx="128" cy="62" r="5" fill="#C9A227"/>
    `;
  }
  // 17. ĐỒNG HỒ / CLOCK
  else if (/clock|đồng hồ|watch/i.test(p)) {
    subjectSvg = `
      <!-- Art Deco Clock Face -->
      <circle cx="128" cy="128" r="54" fill="#F4EAD5" stroke="#C9A227" stroke-width="4"/>
      <circle cx="128" cy="128" r="48" fill="none" stroke="#18181B" stroke-width="1.5"/>
      <!-- 4 Vạch giờ chính 12, 3, 6, 9 -->
      <rect x="126" y="82" width="4" height="10" fill="#18181B"/>
      <rect x="126" y="164" width="4" height="10" fill="#18181B"/>
      <rect x="82" y="126" width="10" height="4" fill="#18181B"/>
      <rect x="164" y="126" width="10" height="4" fill="#18181B"/>
      <!-- Kim giờ & kim phút chỉ 10h10 thanh lịch -->
      <line x1="128" y1="128" x2="108" y2="102" stroke="#18181B" stroke-width="4" stroke-linecap="round"/>
      <line x1="128" y1="128" x2="152" y2="98" stroke="#18181B" stroke-width="3" stroke-linecap="round"/>
      <circle cx="128" cy="128" r="5" fill="#C9A227"/>
    `;
  }
  // 18. ĐỐI TƯỢNG BẤT KỲ KHÁC (GENERIC ART DECO EMBLEM)
  else {
    const col1 = hash[0] % 2 === 0 ? '#18181B' : '#1E6E6B';
    const col2 = '#C9A227';
    subjectSvg = `
      <!-- Art Deco Geometric Emblem for: ${p} -->
      <!-- Bệ đỡ đối tượng -->
      <polygon points="70,180 186,180 176,192 80,192" fill="${col2}" stroke="#18181B" stroke-width="2"/>
      <!-- Hình khối chính tâm -->
      <rect x="94" y="98" width="68" height="68" rx="6" transform="rotate(45 128 132)" fill="${col1}" stroke="${col2}" stroke-width="3"/>
      <circle cx="128" cy="132" r="28" fill="${col2}" stroke="#18181B" stroke-width="2"/>
      <circle cx="128" cy="132" r="14" fill="#F4EAD5"/>
      <!-- Tia sáng 4 phương -->
      <line x1="128" y1="72" x2="128" y2="88" stroke="${col2}" stroke-width="3"/>
      <line x1="128" y1="176" x2="128" y2="192" stroke="${col2}" stroke-width="3"/>
      <line x1="68" y1="132" x2="84" y2="132" stroke="${col2}" stroke-width="3"/>
      <line x1="172" y1="132" x2="188" y2="132" stroke="${col2}" stroke-width="3"/>
    `;
  }

  // Khung viền Art Deco tổng thể theo style.yaml (Gold #C9A227, Cream #F4EAD5, Chevron)
  const fullSvg = `
  <svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
    <!-- Nền Cream chuẩn Art Deco -->
    <rect width="256" height="256" fill="#F4EAD5"/>
    
    <!-- Tia sáng Sunburst nền Art Deco thanh lịch -->
    <g opacity="0.16" stroke="#C9A227" stroke-width="1.5">
      <line x1="128" y1="128" x2="20" y2="20"/>
      <line x1="128" y1="128" x2="128" y2="10"/>
      <line x1="128" y1="128" x2="236" y2="20"/>
      <line x1="128" y1="128" x2="246" y2="128"/>
      <line x1="128" y1="128" x2="236" y2="236"/>
      <line x1="128" y1="128" x2="128" y2="246"/>
      <line x1="128" y1="128" x2="20" y2="236"/>
      <line x1="128" y1="128" x2="10" y2="128"/>
    </g>

    <!-- Khung viền đôi Art Deco Stepped Chevron -->
    <rect x="7" y="7" width="242" height="242" fill="none" stroke="#C9A227" stroke-width="2.5"/>
    <rect x="12" y="12" width="232" height="232" fill="none" stroke="#18181B" stroke-width="1"/>
    
    <!-- 4 Góc Stepped Chevron Art Deco -->
    <polygon points="7,7 28,7 28,12 12,12 12,28 7,28" fill="#C9A227"/>
    <polygon points="249,7 228,7 228,12 244,12 244,28 249,28" fill="#C9A227"/>
    <polygon points="7,249 28,249 28,244 12,244 12,228 7,228" fill="#C9A227"/>
    <polygon points="249,249 228,249 228,244 244,244 244,228 249,228" fill="#C9A227"/>

    <!-- Đối tượng chính ở trung tâm (Rõ ràng 100%, con heo ra con heo, cái bàn ra cái bàn) -->
    ${subjectSvg}
  </svg>
  `;

  const resvg = new Resvg(fullSvg, { fitTo: { mode: 'width', value: 256 } });
  return resvg.render().asPng();
}

module.exports = {
  generateArtDecoSvg,
};
