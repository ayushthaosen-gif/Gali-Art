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

/* Scenes: frames placed on the wall image by real millimetres. data-scene-mm is how many mm the scene's full width represents (the
   scene is 4:3); each frame's data-at="x,y" is its centre in mm from the scene centre (y down). Sizes come from FramePreview.geometry. */
document.querySelectorAll(".scene[data-scene-mm]").forEach(scene => {
  const sceneW = Number(scene.dataset.sceneMm), sceneH = sceneW * 3 / 4;
  scene.querySelectorAll(".framed[data-at]").forEach(frame => {
    const [x, y] = frame.dataset.at.split(",").map(Number);
    const [w, h] = FramePreview.geometry(frame.dataset.size, frame.dataset.frame, frame.dataset.mat === "true").outer;
    frame.style.width = `${w / sceneW * 100}%`;
    frame.style.left = `${50 + (x - w / 2) / sceneW * 100}%`;
    frame.style.top = `${50 + (y - h / 2) / sceneH * 100}%`;
  });
});
