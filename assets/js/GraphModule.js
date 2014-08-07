angular.module("graphApp", [])
    .config(function($interpolateProvider){
        $interpolateProvider.startSymbol('{[').endSymbol(']}');
     })
    .controller('graphCtrl', function($scope, $http, accessKey, token) {
        var _removeKinds = function _removeKinds(data, kinds){
            for(var outer=0; outer < kinds.length; outer++){
                var target_kind = kinds[outer].name;

                // First column is always Timestamp
                for(var inner=1; inner < data.cols.length; inner++){
                  if(data.cols[inner].id == target_kind){
                      data.cols.splice(inner,1);
                      for(var inner_inner=0; inner_inner < data.rows.length; inner_inner++){
                          data.rows[inner_inner].c.splice(inner,1);
                      }
                      break;
                  }
                }
            }
            return data;
        };

        var _drawGraph = function _updateGraph(data){
           for(i = 0 ; i < data.rows.length; i++){
             data.rows[i].c[0].v = new Date(data.rows[i].c[0].v);
           }

           var remove_kinds = $.grep($scope.appInfo.kinds, function(check_kind){
               return check_kind.selected == false ? true : false;
           });

           data = _removeKinds(data, remove_kinds);

           var dataset = Array();
           if($scope.separatedGraph){
              for(var outer=0; outer < $scope.appInfo.kinds.length; outer++){
                var new_data = $.extend(true, [], data);
                var target_kind = $scope.appInfo.kinds[outer].name;
                var remove_kinds = $.grep($scope.appInfo.kinds, function(check_kind){
                    return check_kind.name != target_kind ? true: false;
                });

                new_data = _removeKinds(new_data, remove_kinds);
                dataset.push({"kind": target_kind, "data":new_data});
              }
           }else{
              dataset.push({"kind": $scope.appInfo.name, "data":data});
           }

           $("#charts-frame").empty();
           for(var i=0; i < dataset.length; i++){
               if(dataset[i].data.cols.length <= 1){
                  // Data is not enough to draw a graph
                  continue;
               }

               $("#charts-frame").append('<div id="chart_' + i + '"class="chart"></div>');
               var t_data = new google.visualization.DataTable(dataset[i].data);
               var options = {
                  title: dataset[i].kind
               };
               var chart = new google.visualization.LineChart(document.getElementById("chart_" + i));
               chart.draw(t_data, options);
           }
        };

        $http.get("/api/v1/" + accessKey + "/info/",
                  {
                    params: {"token": token}
                  })
         .success(function(data) {
           $scope.appInfo = data;
           for(i=0; i < $scope.appInfo.kinds.length; i++){
               $scope.appInfo.kinds[i] = {"name": $scope.appInfo.kinds[i],
                                          "selected": true};
           }

           // Graph Initialization
           $scope.updateGraph();

         });

        $scope.redrawGraph = function redrawGraph(){
          _drawGraph($.extend(true, [], $scope.data));
        };

        $scope.updateGraph = function updateGraph(){
           $http.get("/api/v1/" + accessKey + "/data/",
                  {
                    params: {"token": token}
                  })
             .success(function(data) {
                $scope.data = data;
                $scope.redrawGraph();
             });
        };

        $scope.shareGraph = function shareGraph(){

          $http({
                url: "/api/v1/" + $scope.appInfo.name + "/accessible-users/",
                params: {"token": token},
                data: {"email": $scope.shareTo},
                method : 'POST',
          })
          .error(function(data) {
              alert(data.message);
          })
          .success(function(data) {
              alert(data.message);
          });
        };

        $scope.syncing = false;

        $scope.connectChannel = function(){
            $http.get("/api/v1/" + accessKey + "/channel-info/",
                  {
                    params: {"token": token}
                  })
             .success(function getChannelInfoSuccess(data) {
               $scope.channelInfo = data;
               $scope.channel = new goog.appengine.Channel( $scope.channelInfo.channel_token );
               $scope.socket = $scope.channel.open();
               $scope.socket.onopen = function socketOnOpen(){
                    $scope.$apply(function(){
                        $scope.syncing = true;
                    });
                };
                $scope.socket.onmessage = function socketOnMessage(){
                    $scope.updateGraph();
                }
                $scope.socket.onerror = function socketOnError(error){
                    console.log(error);
                };
                $scope.socket.onclose = function socketClosed(){
                    $scope.$apply(function(){
                        $scope.syncing = false;
                    });
                };
            });
         };

        $scope.connectChannel();
    });