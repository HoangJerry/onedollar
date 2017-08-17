var app = require('express')();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var mysql = require('mysql');
var redis = require('redis');
var user_id = null;

app.get('/', function(req, res){
  res.sendFile(__dirname + '/index.html');
});

var connection = mysql.createConnection({
  host     : 'localhost',
  user     : 'root',
  password : 'vibongda123x@X',
  database : 'onedollar'
});

io.use(function(socket, next) {
  if (socket.handshake.query.token) {
    connection.query(
      'SELECT user_id FROM `authtoken_token` WHERE `key` = ?', 
      [socket.handshake.query.token], 
      function(errors, results, fields) {
        if (results.length == 0) {
          next(new Error('Authentication error'));
        } else {
          socket.user_id = results[0]['user_id'];
          next();
        }
      }
    );
  }
});

io.on('connection', function(socket) {
  console.log('>>> user_id: ' + socket.user_id);
  var client = redis.createClient();
  var subscribe_client = redis.createClient();

  // Grab message from Redis and send to client
  subscribe_client.on('message', function(channel, message){
      socket.emit('chat message', message);
  });

  var subscribe_user_key = 'notifications.user.' + socket.user_id;
  subscribe_client.subscribe(subscribe_user_key);
  client.set(subscribe_user_key, 1);

  socket.on('join', function(product_id) {
    connection.query(
      'SELECT COUNT(*) AS `product_exists` FROM `onedollar_product` WHERE `id` = ?', 
      [product_id],
      function(errors, results, fields) {
        if (results && results[0] && results[0]['product_exists']) {
          console.log('>>> join product_id: '+product_id);
          var subscribe_product_key = 'comments.product.' + product_id;
          subscribe_client.subscribe(subscribe_product_key);
        }
      }
    )
  });

  socket.on('leave', function(product_id) {
    console.log('>>> leaving product_id: '+product_id);
    var subscribe_product_key = 'comments.product.' + product_id;
    subscribe_client.unsubscribe(subscribe_product_key);
  });

  socket.on('disconnect', function() {
    console.log('unsubscribe all');
    subscribe_client.unsubscribe();
    client.del(subscribe_user_key);
  });

  socket.on('chat message', function(msg) {
    io.emit('chat message', msg);
  });
});

http.listen(3000, function(){
  console.log('listening on *:3000');
});
