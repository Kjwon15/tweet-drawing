function handleDeleteDrawing(event) {
  var target = $(event.target);
  var statusId = target.attr('data-statusid');
  $.ajax({
    url: URLS.deleteDrawing,
    method: 'delete',
    data: {
      'status_id': statusId,
    },
    success: function(data) {
      target.closest('.mdl-card').remove();
    },
    error: function(xhr, status, error) {
      showToast(error);
    }
  })
}

$(function() {
  $(document.body).on('click', 'button.delete_drawing', handleDeleteDrawing);
})
