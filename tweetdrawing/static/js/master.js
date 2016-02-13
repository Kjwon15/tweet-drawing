function showToast(msg) {
  var container = document.querySelector('#toast-box');
  container.MaterialSnackbar.showSnackbar({message: msg});
}
