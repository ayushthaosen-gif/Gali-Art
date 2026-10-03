/* Supply actual sample photographs here. Empty slots never request an image. */
const SAMPLE_PHOTOS = {
  held: { src: null, alt: "A hand holding the actual Delhi print" },
  shelf: { src: null, alt: "The actual framed Delhi print displayed on a shelf" },
  packaging: { src: null, alt: "The packaging used to deliver a Delhi print" }
};

const room = document.querySelector(".scale-room");
if (room) {
  const photo = room.querySelector(".scale-room-photo");
  const original = document.querySelector(".framed .poster");
  room.querySelectorAll(".scale-print").forEach(slot => slot.append(original.cloneNode(true)));
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
  image.onload = () => { slot.replaceChildren(image); slot.dataset.ready = "true"; };
  image.onerror = () => image.remove();
  slot.append(image);
  image.src = config.src;
});
