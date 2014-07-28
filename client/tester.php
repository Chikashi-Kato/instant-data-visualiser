<?php
require_once("data-connector.php");

$connector = new dataConnector\Connector("73a0a91b479e0f1e3dab5ee622cec9158f83011a5dd92d5d71430f6f0ee36b98", "test");
$data = array("length"=>rand(0, 1000), "processes"=>rand(0,12));
$connector->postData($data);
