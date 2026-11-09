package ai.atlas7.app;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AtlasNativePlugin.class);
        super.onCreate(savedInstanceState);
    }
}
