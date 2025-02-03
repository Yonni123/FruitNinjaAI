```js
window.saveFrame = false;   // Trigger a frame save
window.saveFullFrame = false;   // Trigger a frame save
window.frameNumber = 0;     // Current frame number
window.seq = 0;
window.recordSample = false;// Record a dataset sample (frame + classes)

// Save current content of the canvas
window.doSaveFrame = function(gl) {
    //console.log("Saving frame!");
    var width = gl.canvas.width;
    var height = gl.canvas.height;
    var pixels = new Uint8Array(4 * width * height); // 4 bytes per pixel (RGBA)

    // Read the pixels from the WebGL framebuffer
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

    // Create an image from the pixel data
    var imageData = new ImageData(new Uint8ClampedArray(pixels), width, height);

    // Create a temporary canvas to convert the image data to a base64 PNG
    var tempCanvas = document.createElement("canvas");
    var tempCtx = tempCanvas.getContext("2d");
    tempCanvas.width = width;
    tempCanvas.height = height;

    // Put the image data on the temporary canvas
    tempCtx.putImageData(imageData, 0, 0);

    // Convert the canvas to a base64-encoded PNG
    var imageUrl = tempCanvas.toDataURL("image/png");

    // Create a download link and trigger a download
    var link = document.createElement("a");
    link.href = imageUrl;
    link.download = window.frameName;
    link.click();

    link.remove();
    tempCanvas.remove();
}
```
```js
// The render function that's actually called when an object is rendered
this.render = function( start, count ) {

		gl.drawArrays( mode, start, count );
        if (window.saveFrame) {
            window.saveFrame = false;
            window.doSaveFrame(gl);
            window.gl = gl;
        }
		info.update( count, mode, 1 );

	}
```
```js
// The function that renders the objects one by one
renderObjects = function( renderList, scene, camera ) {

		const overrideMaterial = scene.isScene === true ? scene.overrideMaterial : null;

        const index26 = renderList.findIndex(item => item.id === 26);
        if (index26 !== -1) {
            const [item26] = renderList.splice(index26, 1); // Remove the item with id 26
            renderList.unshift(item26); // Add it to the start of the list
        }

		for ( let i = 0, l = renderList.length; i < l; i ++ ) {
			const renderItem = renderList[ i ];

			const object = renderItem.object;
			const geometry = renderItem.geometry;
			const material = overrideMaterial === null ? renderItem.material : overrideMaterial;
			const group = renderItem.group;

            if (renderItem.id == 26){
                material.map = null;
                material.color.set(0xFFB6C1);
                material.needsUpdate = true;
            }

			if ( camera.isArrayCamera ) {

				const cameras = camera.cameras;

				for ( let j = 0, jl = cameras.length; j < jl; j ++ ) {

					const camera2 = cameras[ j ];

					if ( object.layers.test( camera2.layers ) ) {

						state.viewport( _currentViewport.copy( camera2.viewport ) );

						currentRenderState.setupLightsView( camera2 );

						renderObject( object, scene, camera2, geometry, material, group );

					}

				}

			} else {
                if (renderItem.object.name && renderItem.object.name.length > 3 && window.recordSample) {
                    window.saveFrame = true;
                    window.frameName = window.frameNumber + "-" + window.seq + "-" + renderItem.object.name;
                    window.seq++;
                }
                renderObject( object, scene, camera, geometry, material, group );
			}

		}
        if(window.recordSample){
            window.saveFullFrame = true;
        }
	}
```
```js
renderer.postRender = function ()
    {
        if (this.contextLost) { return; }

        this.flush();

        this.emit(Events.POST_RENDER);

        var state = this.snapshotState;

        if (state.callback)
        {
            WebGLSnapshot(this.canvas, state);

            state.callback = null;
        }

        if (this.textureFlush > 0)
        {
            this.startActiveTexture++;
            this.currentActiveTexture = 1;
        }

        const phasercanv = document.querySelector("#enable3d-phaser-canvas");
        const mainCanv = document.querySelector("#enable3d-three-canvas")
        if (phasercanv && window.saveFullFrame) {
            window.saveFullFrame = false;
            window.frameName = window.frameNumber + "-x-EntireFrame";
            window.recordSample = false;

            const imageURL = phasercanv.toDataURL("image/png");
            const downloadLink = document.createElement('a');
            downloadLink.href = imageURL;
            downloadLink.download =  window.frameName;
            downloadLink.click();

            window.frameNumber++;
            window.seq = 0;
        }
        if (mainCanv && window.saveFullFrame) {
            window.frameName = window.frameNumber + "-x-EntireFrameAgain";
            const imageURL = mainCanv.toDataURL("image/png");
            const downloadLink = document.createElement('a');
            downloadLink.href = imageURL;
            downloadLink.download =  window.frameName;
            downloadLink.click();
        }
    }
```
```js
window.mainS = this
```
```js
setInterval(() => {
    if(window.mainS.gameState == 2){
        window.recordSample = true;
    }
}, 500);

// Start recording dataset samples at regular interval
window.recording = setInterval(() => {
    window.recordSample = true;
}, 500);	//Once every second

// Stop recording
clearInterval(recording);
```