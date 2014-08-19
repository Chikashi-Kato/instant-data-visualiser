<?php
require_once("data-connector.php");

$connector = new dataConnector\Connector("Token-Here", "sample");
$data = array("rand_1000"=>rand(0, 1000), "rand_50"=>rand(0,50));
$connector->postData($data);
