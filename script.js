// 获取统计信息并更新页面
function refreshStats() {
    $.ajax({
      type: 'GET',
      url: '/get-stats',
      success: function (stats) {
        $('#visitCount').text(stats.visitCount);
        $('#uniqueIP').text(stats.uniqueIP);
      },
      error: function (error) {
        console.error('Error getting stats:', error);
      }
    });
  }
  
  $(document).ready(function () {
    $('#recordButton').on('click', function () {
      // 发送 AJAX 请求记录访问者的IP和访问时间
      $.ajax({
        type: 'GET',
        url: '/record-access',
        success: function (response) {
          alert(response.message);
          // 刷新统计信息
          refreshStats();
        },
        error: function (error) {
          console.error('Error recording access:', error);
        }
      });
    });

    $('#apiButton').on('click', function () {
        window.location.href = '/api';
      });
    // 初始加载统计信息
    refreshStats();
  });
  