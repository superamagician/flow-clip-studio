# Meta Prompt: Product Ad Clip Studio (วางรูป/ลิงก์สินค้า → คลิปโฆษณา)

คัดลอกทั้งหมดด้านล่าง (ตั้งแต่ ` ```` ` ถึง ` ```` `) ไปวางในกล่อง **Create** ของ Google Flow Tool Builder (ทูลใหม่ ไม่ใช่ Edit)

---

## ⚠️ ข้อจำกัดที่ต้องรู้ก่อนใช้ (จริงใจ ไม่ปิดบัง)

1. **Flow Tool ดึงข้อมูลจากลิงก์สินค้าอัตโนมัติไม่ได้จริง** — แซนด์บ็อกซ์ของ Flow ไม่มี external API/fetch ไปเว็บภายนอก ดังนั้น "วางลิงก์ Shopee/Lazada แล้วดึงรูป/ชื่อสินค้าเอง" ทำไม่ได้ตรงๆ **ทางแก้ที่ใช้ได้จริงในทูลนี้:** ให้ผู้ใช้แคปหน้าจอสินค้าจากลิงก์แล้ว **อัปโหลดเป็นรูป** แทน — AI จะวิเคราะห์รูปนั้นด้วย vision (`Flow.generate.text` + `images`) แล้วดึงชื่อ/จุดขาย/ราคาที่อ่านเห็นในภาพมากรอกฟอร์มให้อัตโนมัติ ช่องวางลิงก์ยังมีให้ (เก็บไว้เป็นข้อความอ้างอิงเพิ่มเติมเท่านั้น ไม่ได้ถูกดึงข้อมูลจริง)
2. **ข้อความ/ลายน้ำบนคลิปทำด้วย Canvas overlay ไม่ใช่ AI วาดตัวหนังสือ** — เพราะโมเดล AI เรนเดอร์ภาษาไทยในวิดีโอไม่แม่นยำ (สระ/วรรณยุกต์เพี้ยน) ทูลนี้เลยใช้วิธี "สร้างคลิปพื้นจาก AI (ไม่มีตัวหนังสือ) แล้วเอาไปเบิร์นข้อความ+ลายน้ำทับด้วย Canvas/MediaRecorder ในเบราว์เซอร์" ได้ตัวอักษรคมชัด 100% เปลี่ยนฟอนต์/สี/ตำแหน่งได้อิสระ แต่ไฟล์ที่ export ออกมาจากขั้นตอนนี้จะเป็น `.webm` (ข้อจำกัดของ `MediaRecorder` ในเบราว์เซอร์) — ถ้าต้องการ `.mp4` ให้แปลงต่อด้วยโปรแกรมนอก Flow อีกขั้น
3. **พรีเซนเตอร์เสมือนที่ auto เลือกจะไม่เป๊ะ 100% ทุกซีน** — Nano Banana Pro ล็อกหน้าคนได้ "ค่อนข้างดี" ไม่ใช่สมบูรณ์แบบ อาจต้องกด "สุ่มใหม่" บางซีนที่หน้าเพี้ยน
4. คลิปวิดีโอ = ใช้เครดิต (Omni Flash ≈12 เครดิต/คลิป, Veo 3.1 ≈100 เครดิต/คลิป) ส่วนการวิเคราะห์รูป/แต่งบทเป็นข้อความฟรี (Gemini เท่านั้น)

---

## THE PROMPT (คัดลอกจากบรรทัดถัดไป)

```
📝 Meta Prompt: Product Ad Clip Studio Builder

Role: You are an expert Creative Technologist and Senior React/TypeScript developer building a Tool that runs inside Google Flow's sandbox using ONLY the Flow SDK.
Goal: เปลี่ยนรูปสินค้า (หรือแคปหน้าลิงก์สินค้า) ให้กลายเป็นคลิปโฆษณาสไตล์ TikTok Shop/Shopee Video ความยาวตามที่เลือก มีพรีเซนเตอร์เสมือนที่เข้ากับสินค้า มีข้อความ overlay ฟอนต์/สีเฉพาะตัว และมีลายน้ำ/โลโก้กันก๊อบปี้ ให้ร้านค้าออนไลน์และครีเอเตอร์ใช้ได้เอง
Input ของผู้ใช้: รูปสินค้า (อัปโหลด) หรือรูปแคปหน้าลิงก์สินค้า + ลิงก์สินค้า (ข้อความอ้างอิง ไม่ถูกดึงข้อมูลอัตโนมัติ) + ความยาวคลิปต่อ segment + จำนวน segment + brand kit (ฟอนต์/สี/โลโก้)
Output: วิดีโอโฆษณาที่ต่อกันแล้ว (.webm) พร้อมข้อความ overlay และลายน้ำ ดาวน์โหลดได้

============================================================
1. ARCHITECTURE — แยกไฟล์ตามหน้าที่ (ห้ามยุบรวม)
============================================================
- types.ts — interface + ค่าคงที่ dropdown ทั้งหมด (สัญญาตายตัว)
- services/ai.ts — เฉพาะ Flow.generate.text (vision วิเคราะห์รูปสินค้า, สร้างสตอรี่บอร์ด/บท, เลือกลักษณะพรีเซนเตอร์ตามหมวดสินค้า) — คืน data ล้วน ห้ามมี UI
- services/videoCompose.ts — เฉพาะโค้ด Canvas/MediaRecorder สำหรับเบิร์นข้อความ+ลายน้ำทับวิดีโอ (ดูหัวข้อ 6) — ไม่เรียก SDK
- App.tsx — state ทั้งหมด + pipeline เรียก Flow.generate.image / Flow.generate.video + เรียก videoCompose ต่อท้าย
- components/* — UI ล้วน ห้ามมีการเรียก SDK/Canvas ในนี้
ธีม: Dark Mode (#0e0e0e) accent Blue-500 หน้าเดียวเลื่อนได้
กฎ UI: ทุก section เว้นระยะชัด ห้ามกล่องซ้อนทับ ตัวหนังสือห้ามซ้อน การ์ดสูงเท่ากัน การ์ด max-width ~360px

============================================================
2. DATA MODEL (types.ts)
============================================================
export type SegmentRole = 'hook' | 'feature' | 'cta';
export type PresenterMode = 'auto' | 'uploaded' | 'none';
export type WatermarkPosition = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';

export interface ProductBrief {
  imageMediaId?: string; imageBase64?: string;   // รูปสินค้า/แคปหน้าลิงก์ที่อัปโหลด
  productLink?: string;                           // ข้อความอ้างอิงเท่านั้น ไม่ได้ดึงข้อมูลจริง
  name: string; category: string; keySellingPoints: string[];
  price?: string; targetAudience: string; tone: string;
}

// พรีเซนเตอร์เสมือน — ล็อกด้วย imageMediaId เพื่อให้หน้าเดิมทุกซีน
export interface Presenter {
  mode: PresenterMode;
  description: string;         // AI เขียนขึ้นจากหมวดสินค้า เช่น "young Asian man, gaming aesthetic"
  imageMediaId?: string; imageBase64?: string;    // reference sheet ที่ generate ไว้ครั้งแรก หรือรูปที่ผู้ใช้อัปโหลดเอง
}

// Brand Kit — ล็อกฟอนต์/สี/โลโก้ ให้ทุก segment ใช้ชุดเดียวกัน (เอกลักษณ์เฉพาะร้าน)
export interface BrandKit {
  fontFamily: string;          // ชื่อ Google Font เช่น 'Kanit', 'Prompt', 'Anuphan', 'Mitr', 'Chonburi'
  primaryColor: string;        // hex ข้อความหลัก
  accentColor: string;         // hex กราฟิก/ไฮไลต์
  paletteName: string;         // ชื่อชุดสี (สุ่มจากชุดที่ดูมีเอกลักษณ์ ดูข้อ 5)
  logoMediaId?: string; logoBase64?: string;      // โลโก้ผู้ใช้ (ถ้ามี)
  watermarkText?: string;      // ถ้าไม่มีโลโก้ ใช้ข้อความแทน เช่น "@myshop"
  watermarkPosition: WatermarkPosition;
  watermarkOpacity: number;    // 0.2–0.8
}

export interface Segment {
  id: string; role: SegmentRole; order: number;
  script: string;               // บทพูด/ข้อความที่จะโชว์ (ไทย)
  videoPrompt: string;          // prompt animate (อังกฤษ) — ไม่มีคำสั่งให้ AI วาดตัวหนังสือ (overlay ทำทีหลังด้วย Canvas)
  durationSeconds: 4 | 6 | 8 | 10;
  overlayText: { line: string; timing: [number, number] }[];  // ข้อความที่จะเบิร์นทับ + ช่วงเวลาโชว์ (วินาที)
  status: 'idle' | 'generating' | 'done' | 'error'; progress?: number;
  rawVideoMediaId?: string;     // ผลจาก Flow.generate.video (ยังไม่มีข้อความ/ลายน้ำ)
  composedBlobUrl?: string;     // ผลหลังเบิร์น overlay+ลายน้ำแล้ว (พรีวิวได้)
}

export const SEGMENT_DURATIONS = [4, 6, 8, 10] as const;   // Omni Flash รองรับเท่านี้เท่านั้น ห้ามให้ค่าอื่น
export const FONT_OPTIONS = ['Kanit', 'Prompt', 'Anuphan', 'Mitr', 'Chonburi', 'Taviraj'];  // ฟอนต์ไทยที่ดูมีเอกลักษณ์ ไม่ใช้ฟอนต์ระบบทั่วไป
export const PALETTE_PRESETS = [ /* AI เติมชุดสีคู่กัน 6-8 ชุดที่ดู distinctive ไม่ใช่ฟ้า-ขาว generic ทั้งหมด */ ];

============================================================
3. AI TEXT ENGINE (services/ai.ts) — Flow.generate.text เท่านั้น
============================================================
- analyzeProductImage(imageBase64, productLinkText?): ส่งรูปเข้า vision
    const { text } = await Flow.generate.text(
      `วิเคราะห์รูปสินค้านี้ อ่านชื่อ/ราคา/จุดขายที่เห็นในภาพ ${productLinkText ? `ผู้ใช้แปะลิงก์อ้างอิงมาด้วย (ข้อความเท่านั้น ไม่ใช่ข้อมูลที่ดึงจริง): ${productLinkText}` : ''} ตอบเป็น JSON: {name, category, keySellingPoints:[], price, targetAudience, suggestedTone}`,
      { images: [{ base64: imageBase64 }], systemInstruction: 'You are a product marketing analyst.' }
    );
  → parse ด้วย extractJson() + fallback ถ้า parse ไม่ได้ ให้เว้นฟิลด์ว่างแทนการเดา
- suggestPresenterDescription(brief: ProductBrief): ให้ AI เขียนคำอธิบายพรีเซนเตอร์ที่ "เข้ากับหมวดสินค้า" เช่น สินค้าเกมมิ่ง → นายแบบวัยรุ่นสไตล์เกมเมอร์; สินค้าความงาม → นางแบบโทนอบอุ่น; ไม่ fix ค่าตายตัว ให้ AI ตัดสินจาก category+targetAudience จริง คืน description (อังกฤษ ใช้เป็น image prompt ได้เลย)
- generateStoryboard(brief, presenter, totalSegments, secondsPerSegment): คืน JSON
    { segments: [{ role:'hook'|'feature'|'cta', script, videoPrompt, overlayText:[{line,timing}] }] }
  กติกาที่ต้องใส่ใน prompt: "ถ้า totalSegments=1 ให้ทำ hook+feature+cta อัดในคลิปเดียว, ถ้า=2 แบ่ง hook+feature / cta, ถ้า=3 แบ่งตามบทบาทเป๊ะ" และ "videoPrompt ห้ามสั่งให้มีตัวหนังสือ/ซับในวิดีโอ (STRICTLY NO TEXT, NO SUBTITLES, NO CAPTIONS) เพราะข้อความจะถูกเบิร์นทับทีหลังด้วย Canvas"
- suggestBrandKit(brief): ให้ AI เลือกฟอนต์จาก FONT_OPTIONS + สร้างชุดสี primary/accent ที่ "ไม่ใช่ฟ้า-ขาวหรือแดง-เหลือง generic ที่ใครก็ใช้" ให้จับคู่กับโทนสินค้า (เช่น สินค้าเกมมิ่ง → นีออน/ไซเบอร์; สินค้าออร์แกนิก → เอิร์ธโทน) คืน {fontFamily, primaryColor, accentColor, paletteName}
ทุกฟังก์ชัน parse JSON ด้วย extractJson() + try/catch fallback เสมอ (model อาจห่อ JSON ด้วยข้อความ)

============================================================
4. IDENTITY-LOCK พรีเซนเตอร์ (App.tsx)
============================================================
- ถ้า presenter.mode==='uploaded': ใช้รูปผู้ใช้อัปโหลดเป็น imageMediaId ล็อกตรงๆ
- ถ้า presenter.mode==='auto' และยังไม่เคย generate: เรียก suggestPresenterDescription แล้ว
    const ref = await Flow.generate.image({
      prompt: `Professional presenter reference sheet, front-facing, neutral background, ${presenter.description}`,
      modelDisplayName: '🍌 Nano Banana Pro', aspectRatio: '9:16'
    });
  เก็บ ref.mediaId ไว้เป็น presenter.imageMediaId ใช้ซ้ำ "ทุกซีนที่มีคน" ตลอดทั้งโปรเจกต์ (ห้าม generate ใหม่ทุกซีน)
- ถ้า presenter.mode==='none': ซีนทั้งหมดเป็น B-roll สินค้าล้วน ไม่มีคน

============================================================
5. VISUAL PIPELINE (App.tsx) — เจนภาพก่อน แล้วค่อย animate (2 phase, resumable)
============================================================
import { Flow } from 'flow-sdk';

const handleGenerateAll = async () => {
  const productRefs = [brief.imageMediaId].filter(Boolean) as string[];
  const presenterRefs = presenter.imageMediaId ? [presenter.imageMediaId] : [];
  const updated = [...segments];

  // PHASE 1 — ภาพต่อซีน (ล็อกสินค้า + พรีเซนเตอร์ทุกซีนที่มีคน)
  for (let i = 0; i < updated.length; i++) {
    if (updated[i].rawVideoMediaId) continue;   // ข้ามซีนที่ทำเสร็จแล้ว
    setProgress(i, 'กำลังวาดฉาก...', 10);
    const refs = updated[i].role === 'feature' ? productRefs : [...productRefs, ...presenterRefs];
    const img = await Flow.generate.image({
      prompt: `Theme: ${brandKit.paletteName}. ${updated[i].videoPrompt}. Cinematic lighting, high detail, no text.`,
      modelDisplayName: '🍌 Nano Banana Pro', aspectRatio: '9:16',
      referenceImageMediaIds: refs.length ? refs : undefined
    });
    updated[i] = { ...updated[i], imageMediaId: img.mediaId, status: 'done' };
    setSegments([...updated]);
  }

  // PHASE 2 — animate ภาพที่ gen เอง (ห้าม animate รูปอัปโหลดดิบ)
  for (let i = 0; i < updated.length; i++) {
    if (updated[i].rawVideoMediaId) continue;
    setProgress(i, 'กำลังทำแอนิเมชัน...', 50);
    const spokenLine = updated[i].script
      ? `The presenter speaks in Thai: "${updated[i].script}". Finish speaking within ${updated[i].durationSeconds} seconds.`
      : '';
    const vid = await Flow.generate.video({
      prompt: `${spokenLine} High fidelity motion. STRICTLY NO TEXT, NO SUBTITLES, NO CAPTIONS, NO OVERLAYS baked into the video.`,
      modelDisplayName: 'Omni Flash',
      aspectRatio: '9:16',
      durationSeconds: updated[i].durationSeconds,
      referenceImageMediaIds: [updated[i].imageMediaId!]
    });
    updated[i] = { ...updated[i], rawVideoMediaId: vid.mediaId,
      rawBase64: vid.base64, rawMimeType: vid.mimeType, status: 'done' };
    setSegments([...updated]);
    await composeOverlayForSegment(i);   // ต่อด้วยขั้นเบิร์น overlay ทันทีที่ raw video เสร็จ (ดูข้อ 6)
  }
};

============================================================
6. POST-PROCESS: เบิร์นข้อความ overlay + ลายน้ำ ด้วย Canvas/MediaRecorder (services/videoCompose.ts)
============================================================
ห้ามพึ่ง AI วาดตัวหนังสือในวิดีโอ (ภาษาไทยเพี้ยนบ่อย) — ให้ประกอบทับด้วยโค้ดฝั่งเบราว์เซอร์แทน ตัวอักษรจะคมชัด 100% แก้ฟอนต์/สี/ตำแหน่งได้อิสระ:

async function composeOverlayForSegment(index: number) {
  const seg = segments[index];
  const videoEl = document.createElement('video');
  videoEl.src = URL.createObjectURL(base64ToBlob(seg.rawBase64, seg.rawMimeType));
  await videoEl.play();  // ต้อง play ก่อนถึงจะ capture เฟรมได้

  const canvas = document.createElement('canvas');
  canvas.width = videoEl.videoWidth; canvas.height = videoEl.videoHeight;
  const ctx = canvas.getContext('2d')!;

  const canvasStream = canvas.captureStream(30);
  const audioTrack = videoEl.captureStream().getAudioTracks()[0];
  if (audioTrack) canvasStream.addTrack(audioTrack);   // เก็บเสียงต้นฉบับไว้ด้วย

  const recorder = new MediaRecorder(canvasStream, { mimeType: 'video/webm;codecs=vp9,opus' });
  const chunks: Blob[] = [];
  recorder.ondataavailable = (e) => chunks.push(e.data);
  const done = new Promise<Blob>((resolve) => {
    recorder.onstop = () => resolve(new Blob(chunks, { type: 'video/webm' }));
  });
  recorder.start();

  const logoImg = brandKit.logoBase64 ? await loadImage(brandKit.logoBase64) : null;

  function drawFrame() {
    ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
    const t = videoEl.currentTime;
    // ข้อความ overlay ตามช่วงเวลาที่กำหนดไว้ใน seg.overlayText
    seg.overlayText.forEach(({ line, timing: [start, end] }) => {
      if (t >= start && t <= end) {
        ctx.font = `bold 48px "${brandKit.fontFamily}"`;
        ctx.fillStyle = brandKit.primaryColor;
        ctx.strokeStyle = brandKit.accentColor; ctx.lineWidth = 6;
        ctx.textAlign = 'center';
        ctx.strokeText(line, canvas.width / 2, canvas.height * 0.75);
        ctx.fillText(line, canvas.width / 2, canvas.height * 0.75);
      }
    });
    // ลายน้ำ/โลโก้ ตำแหน่ง+ความโปร่งใสตาม brandKit
    ctx.globalAlpha = brandKit.watermarkOpacity;
    const pos = watermarkCoords(brandKit.watermarkPosition, canvas.width, canvas.height);
    if (logoImg) ctx.drawImage(logoImg, pos.x, pos.y, 96, 96);
    else if (brandKit.watermarkText) {
      ctx.font = '24px "${brandKit.fontFamily}"'; ctx.fillStyle = '#ffffff';
      ctx.fillText(brandKit.watermarkText, pos.x, pos.y);
    }
    ctx.globalAlpha = 1;
    if (!videoEl.ended) requestAnimationFrame(drawFrame);
    else recorder.stop();
  }
  drawFrame();

  const composedBlob = await done;
  segments[index].composedBlobUrl = URL.createObjectURL(composedBlob);
  setSegments([...segments]);
}

// ต่อหลาย segment เป็นคลิปเดียว: ทำเหมือนกันแต่ concat หลาย <video> เข้า canvas เดียวเรียงต่อกันตามเวลา
// (เล่นตัวแรกจนจบ ค่อยสลับ src เป็นตัวถัดไป แล้ว capture ต่อเนื่องในสตรีมเดียว)

// ดาวน์โหลดผลลัพธ์สุดท้าย:
// await Flow.download({ base64: await blobToBase64(finalBlob), mimeType: 'video/webm', filename: 'ad-clip.webm' });

============================================================
7. UI / UX
============================================================
STEP 1 — Product Brief:
- อัปโหลดรูปสินค้า/แคปหน้าลิงก์ (บังคับ) + ช่องวางลิงก์สินค้า (ข้อความอ้างอิง, ระบุใต้ช่องว่า "ใช้เป็นข้อมูลอ้างอิงเท่านั้น ไม่ได้ดึงข้อมูลจากลิงก์อัตโนมัติ")
- ปุ่ม "🔍 วิเคราะห์สินค้า" → เรียก analyzeProductImage → auto-fill ฟอร์ม name/category/sellingPoints/price/audience/tone (แก้ไขได้ทุกช่อง)

STEP 2 — Presenter:
- เลือกโหมด: "ให้ AI เลือกพรีเซนเตอร์ให้ตามสินค้า (auto)" / "อัปโหลดรูปคนเอง" / "ไม่มีคน (B-roll ล้วน)"
- ถ้า auto: โชว์คำอธิบายที่ AI เขียน + ปุ่ม "สร้าง reference ใหม่" (สุ่มหน้าใหม่ถ้าไม่ถูกใจ) + พรีวิวรูป reference ที่ล็อกไว้

STEP 3 — Clip Settings:
- ความยาวต่อ segment: dropdown จาก SEGMENT_DURATIONS เท่านั้น (4/6/8/10)
- จำนวน segment: 1–3 (การ์ดอธิบาย role ให้เห็น: 1=รวมทุกอย่างในคลิปเดียว, 2=Hook+Feature/CTA, 3=Hook/Feature/CTA แยกเต็ม)
- ปุ่มหัวใจ "✨ ให้ AI แต่งสตอรี่บอร์ดให้ทั้งหมด" → เรียก generateStoryboard เติมทุก segment เป็น final draft ไม่เว้นว่าง แก้ทีหลังได้

STEP 4 — Brand Kit (เอกลักษณ์เฉพาะร้าน):
- ปุ่ม "🎨 ให้ AI สุ่ม Brand Kit ให้เข้ากับสินค้า" → suggestBrandKit เติมฟอนต์+สี ให้ทันที + preview การ์ดตัวอย่างข้อความจริงด้วยฟอนต์/สีที่เลือก
- ให้ผู้ใช้เปลี่ยนฟอนต์ (dropdown FONT_OPTIONS) / สีหลัก / สีรอง (color picker) เองได้เสมอ
- อัปโหลดโลโก้ (ถ้ามี) หรือพิมพ์ข้อความลายน้ำแทน
- เลือกตำแหน่งลายน้ำ (มุมซ้ายบน/ขวาบน/ซ้ายล่าง/ขวาล่าง/กลาง) + สไลเดอร์ความโปร่งใส 20–80%

STEP 5 — Segment Cards (แก้ทีละซีนได้):
- พรีวิววิดีโอจริง (composedBlobUrl) หลัง compose เสร็จ, แก้ script/overlayText ได้, ปุ่ม "สร้างใหม่เฉพาะซีนนี้"
- แถบ progress ต่อซีน (simulate 2–5%/300–500ms, cap 90–95%, snap 100% ตอนเสร็จจริง — ห้ามกระโดด 0→100)

STEP 6 — Export:
- ปุ่ม "รวมทุก segment เป็นคลิปเดียว + ดาวน์โหลด (.webm)"
- แจ้งเตือนชัดเจนว่าไฟล์เป็น .webm ถ้าต้องการ .mp4 ให้แปลงต่อนอกทูล

============================================================
8. LOCALIZATION
============================================================
- UI ไทยทั้งหมด, เนื้อหา/บทพูดไทยมืออาชีพ ไม่แปลตรงตัว
- videoPrompt (ส่งเข้า Flow.generate.video/image) เป็นภาษาอังกฤษเสมอ และต้องมีวรรค "STRICTLY NO TEXT, NO SUBTITLES, NO CAPTIONS" ทุกครั้ง เพราะข้อความทั้งหมดถูกเบิร์นทับทีหลังด้วย Canvas ไม่ใช่ให้ AI วาด
```

(จบ THE PROMPT)

---

## หมายเหตุสำหรับผู้ใช้ (ไม่ต้องคัดลอกส่วนนี้)

- ทูลนี้ต่อยอดจากโครงสร้าง 3-segment (Hook → Feature/B-roll → CTA) ที่แกะได้จริงจาก [master-prompt-หูฟัง-gaming-headset.md](master-prompt-หูฟัง-gaming-headset.md) — ใช้เป็นตัวอย่างทดสอบทูลได้เลยหลังสร้างเสร็จ
- ถ้า Gemini เขียนโค้ดรอบแรกแล้วมีจุดพัง ให้ส่งสกรีนช็อตปัญหามาบอก จะช่วยเขียน **Edit Prompt** สั้นๆ แก้เฉพาะจุดนั้นให้ (ไม่ต้อง rebuild ใหม่ทั้งหมด เว้นแต่โครงสร้างข้อมูลเปลี่ยน)
- ส่วนที่เสี่ยงพังบ่อยที่สุดคือขั้นตอน Canvas/MediaRecorder (ข้อ 6) เพราะเป็นโค้ดที่ซับซ้อนกว่าปกติ — ถ้า Gemini เขียนแล้ว error ให้ลองขอให้มัน "ทำให้ทีละสเต็ป ตรวจ videoEl.readyState ก่อน draw ทุกเฟรม" เป็น Edit Prompt ต่อได้
