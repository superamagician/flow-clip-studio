# Master Prompt: โฆษณาหูฟังเกมมิ่ง KOTION EACH G2000 (ชุด 3 ตัวแปร + คลิปรวม)

## ข้อมูลไฟล์ต้นฉบับ

| ไฟล์ | ความยาว | ความละเอียด/อัตราส่วน | fps | เสียง |
|---|---|---|---|---|
| `1.1._หูฟัง_..._20.mp4` (เรียกว่า **v1**) | 10.08s | 304×540 (~9:16) | 24 | มี (aac) |
| `2.1._หูฟัง_..._20.mp4` (เรียกว่า **v2**) | 10.08s | 304×540 (~9:16) | 24 | มี (aac) |
| `3.1._หูฟัง_..._20.mp4` (เรียกว่า **v3**) | 10.08s | 304×540 (~9:16) | 24 | มี (aac) |
| `1. หูฟัง หูฟังมีไฟ (ทดสอบ).mp4` (เรียกว่า **test30**) | 30.02s | 304×540 (~9:16) | 24 | มี (aac) |

**ข้อสังเกตสำคัญ (ยืนยันด้วยการเทียบเฟรมจริง ไม่ใช่การเดา):** `test30` คือ **v1 + v2 + v3 ต่อกันเป็นคลิปเดียว** แบบเรียงลำดับตรงตามชื่อไฟล์ (1→2→3) แถมลายน้ำ **"7Things"** ทับทุกเฟรม โดยความยาวรวมจริง (30.02s) สั้นกว่าผลรวมสามคลิปแยก (30.25s) ประมาณ 0.23 วินาที — สอดคล้องกับการตัดต่อรอยต่อสั้นๆ ระหว่างสติช (จุดไม่แน่ใจ: อาจมีการ crossfade หรือตัดปลาย/ต้นคลิปแต่ละท่อนเล็กน้อย ไม่สามารถยืนยันเฟรมที่แน่นอนที่สุดได้)

นี่คือตัวอย่างจริงของรูปแบบ "generate ทีละ ~10 วินาทีต่อคลิป แล้วเอามาต่อกัน (stitch)" ที่ใช้กับ Google Flow REST ได้โดยตรง — v1/v2/v3 คือ 3 **ตัวแปร hook/มุมขาย (A/B/C)** ของสินค้าเดียวกัน ไม่ใช่ 3 ช็อตของเรื่องเดียวกัน

## โครงสร้างเรื่องโดยรวม

สินค้าเดียวกันตลอด (**หูฟังเกมมิ่ง แบรนด์ "KOTION EACH" รุ่น "G2000"** สีดำ-น้ำเงิน มีไฟ LED สีฟ้ารอบกรอบหูและใกล้บูมไมค์ มีสายไมค์บูม) พรีเซนเตอร์คนเดียวกันตลอด (ผู้ชายเอเชีย ผมสั้นดำ สวมแว่นตากรอบดำหนา นั่งเก้าอี้เกมมิ่งสีดำ-แดงหรือโต๊ะเกมมิ่ง มีจอคอม/เคสพีซีไฟ RGB เป็นฉากหลัง)

| ตัวแปร | โครงสร้าง (สูตรขายของสั้น) | จุดขายหลักที่เน้น |
|---|---|---|
| **v1** | Hook (ปัญหา) → เผยสินค้า (dramatic reveal) → โชว์ฟีเจอร์ไมค์ → พรีเซนเตอร์ยิ้ม/โป้งขึ้น (พอใจ) | แก้ปัญหาเสียง/ไมค์ไม่ดี |
| **v2** | ไม่มี hook แบบพูด — เปิดด้วย B-roll โปรดักต์ + ข้อความสรุปสเปกทยอยขึ้นทับ → ตัดไปคนใช้งานจริงหน้าคอม → ปิดด้วย B-roll โปรดักต์ในบรรยากาศห้องเกม | ลิสต์สเปก (มีไมค์ / มีไฟ / ทรงเกมมิ่ง) |
| **v3** | Hook (อัปเกรดโต๊ะคอม) → พรีเซนเตอร์พูดต่อ → ท่าทางชี้ลง (CTA gesture) → B-roll โปรดักต์ + แบนเนอร์ CTA ใหญ่ | กระตุ้นให้กดตะกร้า/ซื้อ |

---

## รายละเอียดรายช็อต (Verbatim Spec)

### v1 — "เสียงไม่อิน ไมค์ไม่มา" (Hook → Reveal → Feature → Happy)

| เวลา (in–out) | ประเภทช็อต | กรอบภาพ/กล้อง | ตัวแบบ/ฉาก | แสง/โทนสี | ข้อความบนจอ (verbatim) | หมายเหตุ |
|---|---|---|---|---|---|---|
| 0.00–5.50s | Talking-head (hook) | Medium close-up, static | พรีเซนเตอร์ทำหน้าบึ้ง/หงุดหงิดเล็กน้อย ถือหูฟังอินเอียร์สีดำแบบเรียบๆ (ไม่ใช่สินค้าที่ขาย) ไว้สองข้างมือ ยกขึ้นระดับหน้าอก นั่งเก้าอี้เกมมิ่งดำ-แดง ฉากหลังห้อง ผนังขาว มีจอคอม/แอร์ | แสงห้องปกติ โทนขาว-เทา นวล | "เสียงไม่อิน?" (บรรทัดบน) / "ไมค์ไม่มา?" (บรรทัดล่าง) — ตัวอักษรตัวหนาสีสลับ (ฟ้า/เหลือง/ชมพู) มีไอคอนสายฟ้า/ลูกศรกระจายรอบข้อความ แบบป็อปอัพ | อุปกรณ์ที่ถือในช็อตนี้เป็นหูฟังคู่แข่ง/ปัญหา ไม่ใช่สินค้าที่ขายจริง — ใช้เป็น prop แทนปัญหา |
| 5.50–7.46s | Product macro (dramatic reveal) | Extreme close-up, static, พื้นหลังดำสนิท | หูฟัง KOTION EACH G2000 ลอยอยู่บนขาตั้ง ไฟ LED สีฟ้าสว่างรอบกรอบหูและขอบแถบคาดศีรษะ | พื้นหลังดำ, ไฟหลักสีฟ้าอมขาวจากตัวสินค้าเอง, contrast สูงมาก mood ดราม่า | ไม่มี | เห็นโลโก้ "KOTION EACH" และเลขรุ่น "G200x" สลัวๆ บนตัวเครื่อง |
| 7.46–9.00s | Product macro (feature: mic) | Extreme close-up ที่ปลายบูมไมค์, มี rack focus เล็กน้อย | ปลายไมค์บูมทรงหกเหลี่ยม มีวงแหวนแสงฟ้าเรืองรอบปลายไมค์ (เอฟเฟกต์แอนิเมชันวงแหวนขยายแบบ pulse) ฉากหลังเบลอเป็นจอคอมและคีย์บอร์ด RGB | โทนฟ้าเข้ม เน้นแสงจากปลายไมค์เป็นจุดสนใจ | ไม่มี | เอฟเฟกต์วงแหวนแสงคล้าย "sound wave / mic active" indicator |
| 9.00–10.08s | Talking-head (payoff) | Medium close-up, static | พรีเซนเตอร์สวมหูฟังแล้ว ยิ้มแบบพอใจ ช่วงท้ายชู "นิ้วโป้ง" (thumbs up) มือซ้าย | แสงห้องปกติเหมือนช็อตแรก | ไม่มี | ปิดคลิปด้วยสีหน้า/ท่าทางเชิงบวก ไม่มี CTA ข้อความ |

### v2 — "มีไมค์ มีไฟ ทรงเกมมิ่ง" (Feature-list B-roll)

| เวลา (in–out) | ประเภทช็อต | กรอบภาพ/กล้อง | ตัวแบบ/ฉาก | แสง/โทนสี | ข้อความบนจอ (verbatim) | หมายเหตุ |
|---|---|---|---|---|---|---|
| 0.00–1.54s | Product macro | Close-up 3/4 มุม, พื้นหลังดำ | หูฟังลอยเฉียง มีกราฟิกสายฟ้าเรืองแสงพาดผ่านด้านหลังสินค้า | ดำสนิท + ไฟฟ้าสีฟ้าสว่างจากสินค้า/กราฟิก | "มีไมค์" (ตัวอักษรใหญ่ ป็อปสไตล์คอมิก มีไอคอนดาว/ประกาย) | |
| 1.54–3.04s | Product macro | Extreme close-up กรอบหูฟังด้านข้าง | รายละเอียดวัสดุกรอบหู เย็บขอบ, แถบไฟฟ้าเรืองข้าง | ดำ + ไฟฟ้าขอบสินค้า | "มีไฟ" | |
| 3.04–4.54s | Product macro | Close-up มุมเฉียงกว่าเดิม เห็นไฟ LED รอบกรอบหูชัดขึ้น | เหมือนช็อตก่อน มุมเปลี่ยน | ดำ + ไฟฟ้า | "มีไฟ" (ซ้ำ ต่อเนื่องจากช็อตก่อน) | อาจเป็นช็อตเดียวที่มีการซูม/ขยับกล้องต่อเนื่อง ระบบตัดฉากจับเป็น 2 ช็อตติดกัน |
| 4.54–6.58s | Product macro | Close-up เห็นโลโก้และไฟด้านล่างกรอบหู | โลโก้ "KOTION EACH" และเลขรุ่น "G2000" อ่านออกชัดเจน | ดำ + ไฟฟ้า | ไม่มี (มีตัวหนังสือแบรนด์ปั๊มบนตัวสินค้าเอง ไม่ใช่กราฟิกแทรก) | |
| 6.58–8.08s | Product macro (hero shot) | Medium close-up มุมกว้างขึ้นเห็นทั้งตัวสินค้า | หูฟังเต็มตัวบนขาตั้ง มีกราฟิกคอมิก (ประกาย, ระเบิดควัน, ลูกศร) ล้อมรอบ | ดำ + ไฟฟ้า | ไม่มีข้อความอ่านออก (มีเฉพาะโลโก้บนตัวสินค้า) | |
| 8.08–10.08s (นับใน v2) | Cut to usage | Medium shot มุมข้าง-หน้า พรีเซนเตอร์นั่งพิมพ์คีย์บอร์ด RGB หน้าจอคอม | พรีเซนเตอร์สวมหูฟัง นั่งเล่นเกม/พิมพ์ที่โต๊ะคอม ห้องมืด มีไฟ RGB จากเคส/คีย์บอร์ด/ผ้าม่านโทนน้ำเงิน-ม่วง | ห้องมืด โทนน้ำเงิน-ม่วงจากไฟ ambient | "ทรงเกม" → เปลี่ยนเป็น "ทรงเกมมิ่ง" (แอนิเมชันข้อความต่อคำ) จากนั้นตัดไปโคลสอัพข้างหน้าพรีเซนเตอร์ (ไม่มีข้อความ) แล้วจบด้วยภาพสินค้าบนโต๊ะพร้อมข้อความซ้อน 3 บรรทัด: **"มีไมค์" / "มีไฟ" / "ทรงเกมมิ่ง"** (สรุปรวมสเปกก่อนจบคลิป) | ปิดท้ายด้วยภาพสินค้าสวยๆ ไม่มีข้อความ (clean hero shot) |

### v3 — "อัปฟีลเกมให้โต๊ะคอม" (Hook → CTA gesture → Cart banner)

| เวลา (in–out) | ประเภทช็อต | กรอบภาพ/กล้อง | ตัวแบบ/ฉาก | แสง/โทนสี | ข้อความบนจอ (verbatim) | หมายเหตุ |
|---|---|---|---|---|---|---|
| 0.00–2.08s | Talking-head (hook) | Medium shot มุมข้าง 3/4 ที่โต๊ะเกมมิ่ง | พรีเซนเตอร์นั่งหน้าคอม สวมหูฟัง มือพิมพ์คีย์บอร์ด เก้าอี้แบรนด์ "GTRACING" เห็นโลโก้ชัดที่พนักพิง | ห้องแสงอุ่นปกติ (ไม่ใช่โทนไฟ RGB มืดแบบ v2) | "อัปฟี้ลเกม" (บรรทัดบน) / "ให้โต๊ะคอม" (บรรทัดล่าง) ตัวหนังสือป็อปสีขาว-ฟ้า มีไอคอนประกายเล็กด้านซ้าย | สะกดตามที่เห็นจริงคือ "อัปฟี้ลเกม" (มีไม้โทเล็กบน อี — อาจเป็นการสะกดเล่นแบบวัยรุ่น) |
| 2.08–5.13s | Talking-head | Close-up ขึ้นมากกว่าเดิม พรีเซนเตอร์ยิ้ม พูดต่อเนื่อง | เหมือนช็อตก่อน โฟกัสหน้าชัดขึ้น | เหมือนเดิม | ไม่มี | เสียงพูด/บทพูดช่วงนี้ไม่สามารถถอดคำต่อคำได้ในระบบนี้ (ดูหัวข้อสคริปต์เสียงด้านล่าง) |
| 5.13–6.50s | Talking-head (CTA gesture) | Close-up, พรีเซนเตอร์ยิ้มกว้าง ยกมือสองข้างชี้นิ้วลงด้านล่างจอ | ท่าทาง "ชี้ลง" คลาสสิกของ TikTok/Shopee ads | เหมือนเดิม | ไม่มีข้อความ แต่มี**ไอคอนกราฟิก** วงกลมแดงมีลูกศร/เคอร์เซอร์ชี้ลง (สื่อถึงปุ่มกดตะกร้า) ปรากฏกลางล่างจอ | |
| 6.50–10.08s | Product macro (CTA banner) | Close-up สินค้าเอียงมุม พื้นหลังมีเส้นแสงนีออนฟ้าพาดทแยง | หูฟัง KOTION EACH เต็มตัว ไฟ LED ฟ้าสว่าง | ดำ + เส้นไฟนีออนฟ้าฉากหลังสไตล์ futuristic | **"พิกัดตะกร้าด้านล่างเลย"** (ข้อความ 2 บรรทัด ตัวหนังสือใหญ่สีเหลือง-ฟ้า อยู่ล่างสุดของเฟรม ค้างจนจบคลิป) | นี่คือ CTA ปิดท้ายมาตรฐานของสาย TikTok Shop/Shopee Video |

---

## สคริปต์เสียง/คำพูด

**เสียงพูด: ไม่สามารถถอดคำต่อคำได้แม่นยำในระบบนี้** — คลิปทั้งหมดไม่มีซับไตเติลเบิร์นที่ตรงกับคำพูดปาก (ข้อความบนจอที่เจอเป็นกราฟิกสรุปสเปก/hook ไม่ใช่ซับบทพูด) และไม่มีเครื่องมือ speech-to-text ที่ใช้งานได้ในสภาพแวดล้อมนี้โดยไม่พึ่งโดเมนที่มักถูกบล็อก จึงไม่แต่งบทพูดขึ้นเอง

สิ่งที่ตรวจสอบได้จริงด้วย `ffmpeg silencedetect` (threshold -30dB, min duration 0.3s) บนคลิป `test30` ทั้ง 30 วินาที: **ไม่พบช่วงเงียบเลยตลอดคลิป** → มีเสียงเพลง/เสียงพื้นหลัง (และ/หรือเสียงพูด) ต่อเนื่องตลอด ไม่มีจังหวะตัดเงียบ (hard pause) ที่ชัดเจน

ถ้าต้องการสคริปต์คำพูดที่แม่นยำ 100% แนะนำให้ผู้ใช้ส่งสคริปต์ต้นฉบับที่ใช้พูดมาเพิ่ม

## เพลง/SFX

- มีเสียงเพลง/ambient ต่อเนื่องตลอดทั้งสามคลิป (ไม่มีช่วงเงียบตามผล silencedetect)
- ช็อตที่มีกราฟิกป็อปอัพ (v1 hook, v2 feature-list) มักมาพร้อม SFX แบบ "swoosh/pop" ตามธรรมเนียมคลิปสไตล์นี้ — **[ไม่ชัดเจน]**: ไม่สามารถยืนยันจังหวะ SFX ที่แน่นอนจากการวิเคราะห์นี้ได้ ต้องฟังเสียงจริงเพื่อ sync ให้ตรงเป๊ะ
- ไม่เดาแนวเพลง/ชื่อเพลง เนื่องจากไม่มีหลักฐานเพียงพอ

---

## Master Prompt (พร้อมใช้ยิง Veo/Flow — แบ่งเป็น 3 ช่วง ~10 วิ ตามต้นฉบับ)

> ใช้กับ `google-flow-rest` skill: `submit --model omni-flash --aspect-ratio portrait --resolution 720p --duration 10` (หรือ duration 8 ถ้าโมเดลไม่รองรับ 10s) ทำทีละ prompt ต่อไปนี้ แล้วต่อคลิปทั้ง 3 เข้าด้วยกัน (stitch) ถ้าต้องการเวอร์ชันรวม 30 วิ

### Segment A (แทน v1 — Hook/Reveal/Feature/Happy)
```
Vertical 9:16 short-form product ad, 10 seconds. Shot 1 (0-5.5s): A young Asian man with short black hair and thick black-framed glasses sits in a black-and-red gaming chair in a bright white room with a computer monitor and air conditioner visible behind him. He frowns slightly, holding a plain black pair of generic earbuds up at chest height in both hands, static medium close-up camera. Bold pop-style Thai text overlay bursts in: "เสียงไม่อิน?" then "ไมค์ไม่มา?" with colorful lightning-bolt and arrow graphics. Shot 2 (5.5-7.5s): Hard cut to an extreme close-up product shot against pure black background — a black-and-blue gaming headset (KOTION EACH G2000 branding visible) glowing with bright blue LED light around the earcups and headband, dramatic high-contrast lighting, static camera. Shot 3 (7.5-9s): Extreme close-up on the hexagonal boom microphone tip, glowing blue with a pulsing light-ring animation, background softly blurred showing a monitor and RGB keyboard, subtle rack focus. Shot 4 (9-10s): Cut back to the same man now wearing the headset, smiling warmly, giving a thumbs-up with his left hand, same bright room lighting as shot 1.
```

### Segment B (แทน v2 — Feature-list B-roll)
```
Vertical 9:16 short-form product ad, 10 seconds, continuing the same black-and-blue gaming headset (KOTION EACH G2000) against a pure black background with glowing blue LED accents. Shot 1 (0-1.5s): Extreme close-up 3/4 angle of the headset floating against black, a glowing blue lightning-graphic streaks behind it, bold comic-style Thai text pops in: "มีไมค์" with star/sparkle icons. Shot 2 (1.5-4.5s): Extreme close-up on the earcup cushion and stitched edge with blue LED trim, text overlay "มีไฟ". Shot 3 (4.5-6.5s): Close-up revealing the "KOTION EACH G2000" logo and light strip clearly. Shot 4 (6.5-8s): Wider hero shot of the full headset on its stand, comic sparkle and smoke-burst graphics around it. Shot 5 (8-10s): Hard cut to the same man now at a dark, moody gaming desk lit by blue-and-purple ambient RGB light from a PC case and keyboard, wearing the headset, typing while looking at his monitor; animated Thai text builds letter by letter "ทรงเกม" then "ทรงเกมมิ่ง", then a close side-profile of his smiling face, then a final clean product beauty shot on the desk with three stacked lines of Thai text: "มีไมค์" / "มีไฟ" / "ทรงเกมมิ่ง".
```

### Segment C (แทน v3 — Hook/CTA gesture/Cart banner)
```
Vertical 9:16 short-form product ad, 10 seconds. Shot 1 (0-2s): The same Asian man with glasses sits at a gaming desk in front of a monitor, hands on a mechanical keyboard, a red-and-black "GTRACING" branded gaming chair visible behind him, warm ambient room lighting (not dark RGB mood). Bold Thai text pops in top-left: "อัปฟี้ลเกม" then "ให้โต๊ะคอม" with a small sparkle icon. Shot 2 (2-5.1s): Closer medium shot, same setting, he smiles and continues speaking. Shot 3 (5.1-6.5s): He smiles broadly and points both index fingers downward toward the bottom of frame; a red circular cursor/arrow icon graphic appears at the bottom center, mimicking a shopping-cart click prompt. Shot 4 (6.5-10s): Cut to a close-up product shot of the black-and-blue gaming headset at an angle against a black background with diagonal glowing blue neon light streaks, large bold yellow-and-blue Thai CTA text at the bottom of frame reading "พิกัดตะกร้าด้านล่างเลย", text remains on screen through the end of the clip.
```

---

## Template แบบเปลี่ยนสินค้าได้ (Reusable Master Prompt Template)

ใช้โครงเดิมทั้งสามช่วง แทนที่เฉพาะตัวแปรต่อไปนี้ ส่วนอื่น (การจัดวางกล้อง, จังหวะตัด, สไตล์แสง, ตำแหน่ง/สไตล์ข้อความ, ลักษณะตัวละคร) คงเดิมทั้งหมด:

- `[PRESENTER_DESC]` — ค่าเริ่มต้น: "young Asian man, short black hair, thick black-framed glasses, gaming chair setup"
- `[PRODUCT_NAME]` — เช่น "KOTION EACH G2000 gaming headset" → เปลี่ยนเป็นสินค้าอื่น
- `[PRODUCT_VISUAL_DESC]` — สี/วัสดุ/ตำแหน่งไฟ LED ของสินค้าจริง
- `[HOOK_LINE_1]` / `[HOOK_LINE_2]` — คู่ประโยค hook แบบตั้งคำถามปัญหา (Segment A) เช่น "เสียงไม่อิน?" / "ไมค์ไม่มา?"
- `[FEATURE_TAG_1..N]` — แท็กสเปกสั้นๆ ที่จะขึ้นทีละคำ (Segment B) เช่น "มีไมค์" / "มีไฟ" / "ทรงเกมมิ่ง"
- `[UPGRADE_HOOK_LINE_1]` / `[UPGRADE_HOOK_LINE_2]` — hook แบบ "อัปเกรด" (Segment C) เช่น "อัปฟี้ลเกม" / "ให้โต๊ะคอม"
- `[CTA_TEXT]` — ข้อความปิดท้าย เช่น "พิกัดตะกร้าด้านล่างเลย"

ถ้าจะเอา template นี้ไปสร้างเป็น Flow Tool ที่รับ input เหล่านี้จริงจากผู้ใช้ปลายทาง ต่อยอดด้วยสกิล `anthropic-skills:google-flow-builder` ได้เลย (เขียน Meta Prompt ให้ Flow Tool Builder สร้างฟอร์มกรอก 8 ตัวแปรข้างต้น แล้วยิงพรอมต์ทั้ง 3 segment ให้อัตโนมัติ)

---

## จุดที่ไม่แน่ใจ / ต้องยืนยันกับผู้ใช้

- สะกดลายน้ำแบรนด์ช่อง: อ่านได้ชัดเจนว่า **"7Things"** ในเฟรมส่วนใหญ่ แต่บางเฟรมความละเอียดต่ำภาพเบลอทำให้ตัวเลข 7 ดูคล้ายตัว T — ยึดตาม "7Things" เป็นหลักเนื่องจากเฟรมคมชัดส่วนใหญ่อ่านได้แบบนี้
- สคริปต์คำพูดจริงในทุกช่วง talking-head (v1 shot 1/4, v3 shot 1-3) **ไม่สามารถถอดคำต่อคำได้** ในระบบนี้ — ถ้าต้องการคำพูดที่ตรงเป๊ะ ต้องขอสคริปต์จากผู้ใช้เพิ่ม
- "อัปฟี้ลเกม" ใน v3: สะกดด้วยไม้เอกที่ "ฟี้" ซึ่งอาจเป็นการสะกดเล่นของทีมตัดต่อ ไม่ใช่คำมาตรฐาน — คัดลอกตามที่เห็นในเฟรมเป๊ะๆ
- SFX/เพลงประกอบ: ยืนยันได้แค่ "ไม่มีช่วงเงียบ" จาก silencedetect เท่านั้น ไม่สามารถระบุจังหวะ/แนวเพลงที่แน่นอนได้
- ความสัมพันธ์ v1/v2/v3 กับ test30 ยืนยันด้วยการเทียบเฟรมภาพเป๊ะ (identical content) แต่ **ไม่ได้ตรวจสอบว่ามี crossfade/trim ที่จุดต่อจริงหรือไม่** (สังเกตแค่ผลรวมความยาวต่างกัน ~0.23 วินาที)
