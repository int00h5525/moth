function concat_elements() {
  console.log("concat_elements");
  let elements = [];
  
  for (let i = 0; i < 20; i += 1) {
    let e = document.getElementById("part" + i);
    if (e !== null) {
      elements.push(e);
    }
  }
  return elements;
}

function concat_update() {
  let out = [];
  for (let e of concat_elements()) {
    switch (e.type) {
    case "checkbox":
      if (e.checked) {
        out.push(e.value);
      }
      break;
    default:
      out.push(e.value);
      break;
    }
  }
  let answer = document.getElementById("answer");
  answer.value = out.join(",");
}

function concat_init() {
  // Ugly hack
  setTimeout( function() {
  for (let e of concat_elements()) {
    e.addEventListener("input", concat_update);
    e.addEventListener("change", concat_update);
  }
  }, 1000);
}

window.addEventListener("load", concat_init);

