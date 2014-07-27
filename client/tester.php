<?php
require_once("data-connector.php");

$connector = new dataConnector\Connector("test");
$data = array("length"=>rand(0, 1000), "processes"=>rand(0,12));
$connector->postData($data);
