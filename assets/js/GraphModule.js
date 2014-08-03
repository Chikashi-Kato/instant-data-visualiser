angular.module("graphApp", [])
    .config(function($interpolateProvider){
        $interpolateProvider.startSymbol('{[').endSymbol(']}');
     })
    .controller('graphCtrl', function($scope, $http, accessKey, token) {
        var _updateGraph = function _updateGraph(data){
           for(i = 0 ; i < data.rows.length; i++){
             data.rows[i].c[0].v = new Date(data.rows[i].c[0].v);
           }
           var t_data = new google.visualization.DataTable(data);
           var options = {
             title: $scope.appInfo.name
           };

           var chart = new google.visualization.LineChart(document.getElementById('chart_div'));
           console.log(chart);
           console.log(t_data);
           chart.draw(t_data, options);
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
         });

        // Graph Initialization
        $http.get("/api/v1/" + accessKey + "/data/",
                  {
                    params: {"token": token}
                  })
         .success(function(data) {
           $scope.data = data;
           _updateGraph(data);
         });

        $scope.updateGraph = function updateGraph(){
           var exclude = new Array();
           for(i=0; i < $scope.appInfo.kinds.length; i++){
               var kind = $scope.appInfo.kinds[i];
               if(kind.selected == false){
                   exclude.push(kind.name);
               }
           }
           $http.get("/api/v1/" + accessKey + "/data/",
                  {
                    params: {"token": token,
                             "exclude": exclude},
                  })
             .success(function(data) {
                $scope.data = data;
                _updateGraph(data);
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
            if($scope.syncing == true){
                return;
            }

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