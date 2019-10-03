<?php 
	# When test finish, write "Test finished!" in a file on the server
	error_reporting(E_ALL);
	$file = fopen("/var/www/html/http_test/finished.txt", "w+") or die("Unable to open file!");
	$data = 'Test finished!' . PHP_EOL;
	fwrite($file, $data);
	fclose($file);
?> 
