/* Generated lifestyle concepts. They are static: the city, theme and text controls never change them. Paths are relative to the page.
   When real photographs exist, set src to the photo, kind to "photo" (which drops the label) and revise the alt text and caption. */
const SAMPLE_PHOTOS = {
  wall: { src: "frame-preview/lifestyle-wall.webp", kind: "generated", alt: "Generated visualisation of an oak-framed Delhi poster on a plaster wall above books and decor" },
  shelf: { src: "frame-preview/lifestyle-shelf.webp", kind: "generated", alt: "Generated visualisation of an oak-framed Delhi print on a shelf" },
  packaging: { src: "frame-preview/lifestyle-packaging.webp", kind: "generated", alt: "Generated concept of a Delhi print beside a kraft mailing tube and tissue" }
};

const room = document.querySelector(".scale-room");
if (room) {
  const photo = room.querySelector(".scale-room-photo");
  function layoutRoom() {
    const imageWidth = photo.naturalWidth || Number(photo.getAttribute("width"));
    const imageHeight = photo.naturalHeight || Number(photo.getAttribute("height"));
    const left = Number(room.dataset.sofaLeft), width = Number(room.dataset.sofaWidth);
    const bottom = Number(room.dataset.printBottom);
    const pixelsPerMm = imageWidth * width / 1800;
    room.querySelectorAll(".scale-print").forEach((slot, index) => {
      const outer = FramePreview.geometry(slot.dataset.size, slot.dataset.frame, false).outer;
      const w = outer[0] * pixelsPerMm / imageWidth;
      const h = outer[1] * pixelsPerMm / imageHeight;
      const centre = left + width * (index + .5) / 3;
      slot.style.width = `${w * 100}%`;
      slot.style.height = `${h * 100}%`;
      slot.style.left = `${(centre - w / 2) * 100}%`;
      slot.style.top = `${(bottom - h) * 100}%`;
    });
  }
  photo.addEventListener("load", layoutRoom);
  layoutRoom();
}

document.querySelectorAll("[data-sample-photo]").forEach(slot => {
  const config = SAMPLE_PHOTOS[slot.dataset.samplePhoto];
  if (!config?.src) return;
  const image = new Image();
  image.alt = config.alt;
  image.loading = "lazy";
  image.decoding = "async";
  image.onload = () => {
    slot.replaceChildren(image); slot.dataset.ready = "true";
    if (config.kind === "generated") { // label sits on the image itself so it survives cropping and screenshots
      const tag = document.createElement("span");
      tag.className = "image-kind"; tag.textContent = "Generated visualisation";
      slot.append(tag);
    }
  };
  image.onerror = () => image.remove();
  slot.append(image);
  image.src = config.src;
});
