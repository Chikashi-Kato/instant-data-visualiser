<?php
require_once("data-connector.php");

$connector = new dataConnector\Connector("eac8e8180445a34e85fa115f420c75383d353572564251a3db1697bc2fa25abc", "test");
$data = array("length"=>rand(0, 1000), "processes"=>rand(0,12));
$connector->postData($data);
